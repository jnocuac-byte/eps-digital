from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import UUID, String, Text, Date, TIMESTAMP, Boolean, ForeignKey, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
	"""Retorna fecha/hora actual en UTC con timezone-aware."""
	return datetime.now(timezone.utc)


class Usuario(Base):
	"""Entidad principal de usuario del sistema EPS."""

	__tablename__ = "usuarios"

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
	numero_documento: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
	fecha_nacimiento: Mapped[datetime] = mapped_column(Date, nullable=False)
	telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
	correo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

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

	# Datos medicos relevantes para la prestacion del servicio.
	tipo_sangre: Mapped[str | None] = mapped_column(String(5), nullable=True)
	alergias: Mapped[str | None] = mapped_column(Text, nullable=True)
	enfermedades_cronicas: Mapped[str | None] = mapped_column(Text, nullable=True)
	medicamentos_actuales: Mapped[str | None] = mapped_column(Text, nullable=True)
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