from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
	Boolean,
	ForeignKey,
	Index,
	SmallInteger,
	String,
	Text,
	TIMESTAMP,
	event,
	text,
)
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Credencial(Base):
	__tablename__ = "credenciales"

	__table_args__ = (
		Index("ix_credenciales_correo", "correo"),
		Index("ix_credenciales_usuario_id", "usuario_id"),
	)

	# Identificador unico de la credencial (PK).
	credencial_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# UUID de referencia al usuario en User Service (sin ForeignKey por independencia).
	usuario_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		nullable=False,
		unique=True,
	)

	# Correo de autenticacion; debe ser unico para evitar duplicados.
	correo: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

	# Hash de la contrasena (nunca almacenar password en texto plano).
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

	# Rol de autorizacion asignado a la credencial.
	rol: Mapped[str] = mapped_column(
		String(50),
		nullable=False,
		default="usuario",
		server_default=text("'usuario'"),
	)

	# Estado de activacion de la credencial.
	activo: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=True,
		server_default=text("true"),
	)

	# Numero de intentos fallidos acumulados para control de bloqueos.
	intentos_fallidos: Mapped[int] = mapped_column(
		SmallInteger,
		nullable=False,
		default=0,
		server_default=text("0"),
	)

	# Fecha/hora hasta la que la cuenta permanece bloqueada (si aplica).
	bloqueado_hasta: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)

	# Indica si el usuario tiene autenticacion de dos factores habilitada.
	tiene_2fa: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=False,
		server_default=text("false"),
	)

	# Fecha/hora de creacion del registro.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=datetime.utcnow,
	)

	# Fecha/hora de ultima actualizacion del registro.
	actualizado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=datetime.utcnow,
		onupdate=datetime.utcnow,
	)

class TokenRecuperacion(Base):
	"""Tokens temporales para recuperacion segura de credenciales."""

	__tablename__ = "token_recuperacion"

	__table_args__ = (
		Index("ix_token_recuperacion_credencial_id", "credencial_id"),
		Index("ix_token_recuperacion_token_hash", "token_hash"),
	)

	# Identificador unico del token de recuperacion (PK).
	token_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Referencia a la credencial propietaria del token.
	credencial_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		ForeignKey("credenciales.credencial_id"),
		nullable=False,
	)

	# Hash unico del token para evitar almacenar el valor en texto plano.
	token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

	# Fecha/hora limite de validez del token.
	expira_en: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

	# Marca si el token ya fue utilizado.
	usado: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=False,
		server_default=text("false"),
	)

	# Fecha/hora de creacion del token.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=datetime.utcnow,
	)


class Registro2FA(Base):
	"""Registros de codigos 2FA emitidos para validar operaciones sensibles."""

	__tablename__ = "registro_2fa"

	__table_args__ = (
		Index("ix_registro_2fa_credencial_id", "credencial_id"),
		Index("ix_registro_2fa_usado_expira_en", "usado", "expira_en"),
	)

	# Identificador unico del registro 2FA (PK).
	registro_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Referencia a la credencial para la que se genera el codigo 2FA.
	credencial_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		ForeignKey("credenciales.credencial_id"),
		nullable=False,
	)

	# Hash del codigo 2FA para no persistir el codigo en claro.
	codigo_hash: Mapped[str] = mapped_column(String(255), nullable=False)

	# Fecha/hora de expiracion del codigo 2FA.
	expira_en: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

	# Marca si el codigo ya fue consumido.
	usado: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=False,
		server_default=text("false"),
	)

	# Fecha/hora de creacion del registro 2FA.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=datetime.utcnow,
	)


class LogAutenticacion(Base):
	"""Bitacora de eventos de autenticacion para auditoria y trazabilidad."""

	__tablename__ = "log_autenticacion"

	__table_args__ = (
		Index("ix_log_autenticacion_credencial_id", "credencial_id"),
		Index("ix_log_autenticacion_creado_en", "creado_en"),
		Index("ix_log_autenticacion_credencial_id_creado_en", "credencial_id", "creado_en"),
	)

	# Identificador unico del evento de autenticacion (PK).
	log_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)

	# Referencia a la credencial asociada al evento.
	credencial_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		ForeignKey("credenciales.credencial_id"),
		nullable=False,
	)

	# Tipo de evento de autenticacion (login/logout/2FA).
	evento: Mapped[str] = mapped_column(String(50), nullable=False)

	# IP de origen del evento (compatible con IPv4 e IPv6 en texto).
	ip_origen: Mapped[str | None] = mapped_column(String(45), nullable=True)

	# User-Agent enviado por el cliente para analisis forense.
	agente_usuario: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Fecha/hora en la que se registro el evento.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=datetime.utcnow,
	)

@event.listens_for(Credencial, "before_insert")
def set_sqlite_uuid_defaults(mapper, connection, target):
	"""Asigna UUID en Python cuando el motor no soporta gen_random_uuid()."""
	if connection.dialect.name != "postgresql" and not target.credencial_id:
		target.credencial_id = uuid.uuid4()

@event.listens_for(TokenRecuperacion, "before_insert")
def set_sqlite_uuid_defaults_token_recuperacion(mapper, connection, target):
	"""Asigna UUID en SQLite cuando no aplica el server_default de PostgreSQL."""
	if connection.dialect.name != "postgresql" and not target.token_id:
		target.token_id = uuid.uuid4()


@event.listens_for(Registro2FA, "before_insert")
def set_sqlite_uuid_defaults_registro_2fa(mapper, connection, target):
	"""Asigna UUID en SQLite cuando no aplica el server_default de PostgreSQL."""
	if connection.dialect.name != "postgresql" and not target.registro_id:
		target.registro_id = uuid.uuid4()


@event.listens_for(LogAutenticacion, "before_insert")
def set_sqlite_uuid_defaults_log_autenticacion(mapper, connection, target):
	"""Asigna UUID en SQLite cuando no aplica el server_default de PostgreSQL."""
	if connection.dialect.name != "postgresql" and not target.log_id:
		target.log_id = uuid.uuid4()
