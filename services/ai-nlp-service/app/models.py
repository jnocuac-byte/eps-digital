from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utc_now() -> datetime:
	"""Retorna la fecha/hora actual en UTC con zona horaria."""
	return datetime.now(timezone.utc)


class Conversacion(Base):
	"""Conversacion entre un usuario y el asistente de IA."""

	__tablename__ = "conversacion"

	conversacion_id: Mapped[PyUUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid4
	)
	usuario_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
	estado: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
	iniciada_en: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False, default=utc_now
	)
	cerrada_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

	# Relacion 1:N con mensajes de la conversacion.
	mensajes: Mapped[list[Mensaje]] = relationship(
		"Mensaje", back_populates="conversacion", cascade="all, delete-orphan"
	)
	# Relacion 1:1 con el resultado de clasificacion de sintomas.
	clasificacion_sintomas: Mapped[Optional[ClasificacionSintomas]] = relationship(
		"ClasificacionSintomas",
		back_populates="conversacion",
		uselist=False,
		cascade="all, delete-orphan",
	)


class Mensaje(Base):
	"""Mensaje individual dentro de una conversacion."""

	__tablename__ = "mensaje"

	mensaje_id: Mapped[PyUUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid4
	)
	conversacion_id: Mapped[PyUUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("conversacion.conversacion_id", ondelete="CASCADE"),
		nullable=False,
	)
	remitente: Mapped[str] = mapped_column(String(20), nullable=False)
	contenido: Mapped[str] = mapped_column(Text, nullable=False)
	creado_en: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False, default=utc_now
	)

	# Relacion inversa hacia la conversacion.
	conversacion: Mapped[Conversacion] = relationship("Conversacion", back_populates="mensajes")


class ClasificacionSintomas(Base):
	"""Resultado de clasificacion de sintomas para una conversacion."""

	__tablename__ = "clasificacion_sintomas"

	clasificacion_id: Mapped[PyUUID] = mapped_column(
		UUID(as_uuid=True), primary_key=True, default=uuid4
	)
	conversacion_id: Mapped[PyUUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("conversacion.conversacion_id", ondelete="CASCADE"),
		nullable=False,
		unique=True,
	)
	terminos_identificados: Mapped[Optional[list[str]]] = mapped_column(
		ARRAY(String), nullable=True
	)
	especialidad_sugerida: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
	nivel_urgencia: Mapped[str] = mapped_column(String(20), nullable=False)
	confianza_modelo: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
	creado_en: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), nullable=False, default=utc_now
	)

	# Relacion inversa 1:1 hacia la conversacion.
	conversacion: Mapped[Conversacion] = relationship(
		"Conversacion", back_populates="clasificacion_sintomas"
	)