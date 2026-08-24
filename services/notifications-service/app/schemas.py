"""Esquemas Pydantic para Notifications Service."""

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field


class NotificacionCreate(BaseModel):
	medico_id: UUID
	tipo: str
	titulo: str
	descripcion: str
	enlace: str | None = None


class NotificacionResponse(BaseModel):
	notif_id: UUID = Field(
		validation_alias=AliasChoices("notif_id", "notificacion_id"),
		serialization_alias="notificacion_id",
	)
	medico_id: UUID
	tipo: str
	titulo: str
	descripcion: str
	leida: bool
	enlace: str | None = None
	creado_en: datetime

	model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
	message: str
	success: bool = True
