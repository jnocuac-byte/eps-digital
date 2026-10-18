from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
	UUID,
	String,
	Date,
	TIMESTAMP,
	Boolean,
	ForeignKey,
	UniqueConstraint,
	event,
	text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.crypto import EncryptedString, blind_index
from app.database import Base

#: Longitud de un indice ciego HMAC-SHA256 en hexadecimal.
HASH_LEN = 64


def utc_now() -> datetime:
	"""Retorna fecha/hora actual en UTC con timezone-aware."""
	return datetime.now(timezone.utc)


class Usuario(Base):
	"""Entidad principal de usuario del sistema EPS."""

	__tablename__ = "usuarios"

	# La unicidad de la PII cifrada se garantiza por los indices ciegos.
	__table_args__ = (
		UniqueConstraint("numero_documento_hash", name="uq_usuarios_numero_documento_hash"),
		UniqueConstraint("correo_hash", name="uq_usuarios_correo_hash"),
	)

	# Identificador unico del usuario (PK).
	usuario_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Datos personales basicos.
	nombres: Mapped[str] = mapped_column(String(100), nullable=False)
	apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
	tipo_documento: Mapped[str] = mapped_column(String(20), nullable=False)
	# PII cifrada en reposo (H-22). El texto cifrado no es determinista, por eso
	# la unicidad se delega al indice ciego (numero_documento_hash).
	numero_documento: Mapped[str] = mapped_column(EncryptedString, nullable=False)
	fecha_nacimiento: Mapped[datetime] = mapped_column(Date, nullable=False)
	telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
	correo: Mapped[str] = mapped_column(EncryptedString, nullable=False)

	# Indices ciegos (HMAC) para busquedas por igualdad y unicidad sobre las
	# columnas cifradas. Se mantienen automaticamente (ver listeners al final).
	numero_documento_hash: Mapped[str] = mapped_column(String(HASH_LEN), nullable=False)
	correo_hash: Mapped[str] = mapped_column(String(HASH_LEN), nullable=False)

	# Trazabilidad de creacion y actualizacion.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)
	actualizado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
		onupdate=utc_now,
	)

	# Relaciones 1:1 con informacion medica y afiliacion.
	informacion_medica: Mapped[InformacionMedica | None] = relationship(
		back_populates="usuario",
		uselist=False,
		cascade="all, delete-orphan",
	)
	afiliacion: Mapped[Afiliacion | None] = relationship(
		back_populates="usuario",
		uselist=False,
		cascade="all, delete-orphan",
	)


class InformacionMedica(Base):
	"""Informacion clinica complementaria asociada a un usuario."""

	__tablename__ = "informacion_medica"

	# Identificador unico del registro medico (PK).
	info_medica_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Relacion 1:1 con Usuario (usuario_id unico).
	usuario_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("usuarios.usuario_id"),
		nullable=False,
		unique=True,
	)

	# Datos medicos relevantes para la prestacion del servicio (HCE cifrada H-22).
	tipo_sangre: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
	alergias: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
	enfermedades_cronicas: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
	medicamentos_actuales: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
	actualizado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
		onupdate=utc_now,
	)

	# Navegacion inversa hacia la entidad Usuario.
	usuario: Mapped[Usuario] = relationship(back_populates="informacion_medica")


class Afiliacion(Base):
	"""Informacion de afiliacion del usuario al sistema EPS."""

	__tablename__ = "afiliaciones"

	# Identificador unico de la afiliacion (PK).
	afiliacion_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Relacion 1:1 con Usuario (usuario_id unico).
	usuario_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("usuarios.usuario_id"),
		nullable=False,
		unique=True,
	)

	# Datos contractuales y estado de la afiliacion.
	tipo_afiliacion: Mapped[str] = mapped_column(String(20), nullable=False)
	numero_poliza: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	estado: Mapped[str] = mapped_column(
		String(20),
		nullable=False,
		default="activo",
		server_default=text("'activo'"),
	)
	fecha_afiliacion: Mapped[datetime] = mapped_column(Date, nullable=False)
	medico_asignado_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)
	actualizado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
		onupdate=utc_now,
	)

	# Navegacion inversa hacia la entidad Usuario.
	usuario: Mapped[Usuario] = relationship(back_populates="afiliacion")


def _calcular_hashes(target: Usuario) -> None:
	"""Recalcula los indices ciegos a partir de los valores en claro del usuario."""
	target.numero_documento_hash = blind_index(target.numero_documento)
	target.correo_hash = blind_index(target.correo, casefold=True)


@event.listens_for(Usuario, "before_insert")
@event.listens_for(Usuario, "before_update")
def _mantener_hashes(mapper, connection, target: Usuario) -> None:  # noqa: ARG001
	"""Mantiene sincronizados los indices ciegos al insertar/actualizar usuarios.

	Permite que ``crud.py`` siga usando ``setattr``/``model_dump`` sin conocer los
	indices ciegos: el hash se calcula aqui, en el flush, a partir del texto plano.
	"""
	_calcular_hashes(target)