from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ConversacionBase(BaseModel):
	"""Campos base para conversaciones."""

	usuario_id: UUID


class ConversacionCreate(ConversacionBase):
	"""Payload para crear una conversacion."""


class ConversacionResponse(BaseModel):
	"""Respuesta de conversacion."""

	model_config = ConfigDict(from_attributes=True)

	conversacion_id: UUID
	usuario_id: UUID
	estado: str
	iniciada_en: datetime
	cerrada_en: datetime | None = None


class MensajeBase(BaseModel):
	"""Campos base para mensajes de chat."""

	conversacion_id: UUID
	remitente: Literal["usuario", "asistente"]
	contenido: str


class MensajeCreate(MensajeBase):
	"""Payload para crear un mensaje."""


class MensajeResponse(BaseModel):
	"""Respuesta de mensaje persistido."""

	model_config = ConfigDict(from_attributes=True)

	mensaje_id: UUID
	conversacion_id: UUID
	remitente: str
	contenido: str
	creado_en: datetime


class ClasificacionSintomasBase(BaseModel):
	"""Campos base de clasificacion de sintomas."""

	conversacion_id: UUID
	terminos_identificados: list[str] | None = None
	especialidad_sugerida: str | None = None
	nivel_urgencia: Literal["urgente", "prioritario", "programable"]
	confianza_modelo: float | None = Field(default=None, ge=0.0, le=1.0)


class ClasificacionSintomasResponse(BaseModel):
	"""Respuesta de clasificacion de sintomas."""

	model_config = ConfigDict(from_attributes=True)

	clasificacion_id: UUID
	conversacion_id: UUID
	terminos_identificados: list[str] | None = None
	especialidad_sugerida: str | None = None
	nivel_urgencia: str
	confianza_modelo: float | None = None
	creado_en: datetime


class ChatRequest(BaseModel):
	"""Solicitud de conversacion con el asistente."""

	mensaje: str
	conversacion_id: UUID | None = None
	usuario_id: UUID | None = None


class ChatResponse(BaseModel):
	"""Respuesta del asistente para el cliente."""

	respuesta: str
	conversacion_id: UUID
	clasificacion: ClasificacionSintomasResponse | None = None