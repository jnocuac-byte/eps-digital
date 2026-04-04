from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TIPOS_SERVICIO_VALIDOS = {
	"medicina_general",
	"especialista",
	"urgencias",
	"laboratorio",
}

ESTADOS_CITA_VALIDOS = {
	"programada",
	"cancelada",
	"atendida",
	"no_asistio",
}


class CitaBase(BaseModel):
	"""Campos base para crear y responder una cita."""

	usuario_id: UUID
	medico_id: UUID
	especialidad_id: UUID
	tipo_servicio: Literal["medicina_general", "especialista", "urgencias", "laboratorio"]
	fecha_cita: date
	hora_inicio: time
	hora_fin: time
	sede_id: UUID
	descripcion_sintomas: str | None = Field(default=None, max_length=3000)

	@field_validator("descripcion_sintomas")
	@classmethod
	def validar_descripcion_sintomas(cls, value: str | None) -> str | None:
		"""Normaliza la descripcion para evitar cadenas vacias."""
		if value is None:
			return None
		value = value.strip()
		return value or None

	@model_validator(mode="after")
	def validar_rango_horas(self) -> CitaBase:
		"""Valida que la hora de fin sea mayor que la hora de inicio."""
		if self.hora_fin <= self.hora_inicio:
			raise ValueError("hora_fin debe ser mayor que hora_inicio")
		return self


class CitaCreate(CitaBase):
	"""Payload de creacion de cita."""


class CitaUpdate(BaseModel):
	"""Payload parcial para actualizar datos de una cita."""

	fecha_cita: date | None = None
	hora_inicio: time | None = None
	hora_fin: time | None = None
	estado: str | None = None

	@field_validator("estado")
	@classmethod
	def validar_estado(cls, value: str | None) -> str | None:
		"""Valida el estado cuando se envia en la actualizacion."""
		if value is None:
			return None
		value = value.strip()
		if value not in ESTADOS_CITA_VALIDOS:
			raise ValueError(
				"estado invalido. Valores permitidos: programada, cancelada, atendida, no_asistio"
			)
		return value

	@model_validator(mode="after")
	def validar_rango_horas(self) -> CitaUpdate:
		"""Si se envian ambas horas, valida que fin sea mayor que inicio."""
		if self.hora_inicio is not None and self.hora_fin is not None:
			if self.hora_fin <= self.hora_inicio:
				raise ValueError("hora_fin debe ser mayor que hora_inicio")
		return self


class CitaResponse(CitaBase):
	"""Respuesta de una cita persistida."""

	cita_id: UUID
	estado: str
	creado_en: datetime
	actualizado_en: datetime

	model_config = ConfigDict(from_attributes=True)

	@field_validator("estado")
	@classmethod
	def validar_estado_respuesta(cls, value: str) -> str:
		"""Verifica que el estado retornado pertenezca al dominio esperado."""
		if value not in ESTADOS_CITA_VALIDOS:
			raise ValueError(
				"estado invalido. Valores permitidos: programada, cancelada, atendida, no_asistio"
			)
		return value


class HistorialEstadoResponse(BaseModel):
	"""Respuesta de cambios historicos de estado de la cita."""

	historial_id: UUID
	cita_id: UUID
	estado_anterior: str
	estado_nuevo: str
	motivo: str | None = None
	realizado_por: UUID
	creado_en: datetime

	model_config = ConfigDict(from_attributes=True)

	@field_validator("estado_anterior", "estado_nuevo")
	@classmethod
	def validar_estados_historial(cls, value: str) -> str:
		"""Valida que los estados del historial sean reconocidos."""
		if value not in ESTADOS_CITA_VALIDOS:
			raise ValueError(
				"estado invalido. Valores permitidos: programada, cancelada, atendida, no_asistio"
			)
		return value


class RecordatorioResponse(BaseModel):
	"""Respuesta de un recordatorio programado para una cita."""

	recordatorio_id: UUID
	cita_id: UUID
	programado_para: datetime
	enviado: bool
	creado_en: datetime

	model_config = ConfigDict(from_attributes=True)


class CancelarCitaRequest(BaseModel):
	"""Payload para cancelar una cita."""

	motivo: str | None = Field(default=None, max_length=1000)

	@field_validator("motivo")
	@classmethod
	def validar_motivo_cancelacion(cls, value: str | None) -> str | None:
		"""Normaliza el motivo para evitar cadenas vacias."""
		if value is None:
			return None
		value = value.strip()
		return value or None


class ReprogramarCitaRequest(BaseModel):
	"""Payload para reprogramar fecha y horario de una cita."""

	nueva_fecha: date
	nueva_hora_inicio: time
	nueva_hora_fin: time

	@model_validator(mode="after")
	def validar_rango_horas(self) -> ReprogramarCitaRequest:
		"""Valida la coherencia del nuevo rango horario."""
		if self.nueva_hora_fin <= self.nueva_hora_inicio:
			raise ValueError("nueva_hora_fin debe ser mayor que nueva_hora_inicio")
		return self
