from __future__ import annotations

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CatalogSchema(BaseModel):
	"""Configuracion comun para habilitar parseo desde objetos ORM."""

	model_config = ConfigDict(from_attributes=True)


class ServicioBase(CatalogSchema):
	nombre: str = Field(min_length=3, max_length=100)
	descripcion: str | None = None
	icono: str | None = None


class ServicioCreate(ServicioBase):
	pass


class ServicioUpdate(CatalogSchema):
	nombre: str | None = Field(default=None, min_length=3, max_length=100)
	descripcion: str | None = None
	icono: str | None = None


class ServicioResponse(ServicioBase):
	servicio_id: UUID
	activo: bool
	creado_en: datetime


class EspecialidadBase(CatalogSchema):
	servicio_id: UUID
	nombre: str = Field(min_length=3, max_length=100)
	descripcion: str | None = None
	duracion_cita_minutos: int = Field(default=20, ge=1, le=240)


class EspecialidadCreate(EspecialidadBase):
	pass


class EspecialidadUpdate(CatalogSchema):
	servicio_id: UUID | None = None
	nombre: str | None = Field(default=None, min_length=3, max_length=100)
	descripcion: str | None = None
	duracion_cita_minutos: int | None = Field(default=None, ge=1, le=240)


class EspecialidadResponse(EspecialidadBase):
	especialidad_id: UUID
	activo: bool
	creado_en: datetime


class MedicoBase(CatalogSchema):
	nombres: str = Field(min_length=2, max_length=100)
	apellidos: str = Field(min_length=2, max_length=100)
	numero_registro: str = Field(min_length=5, max_length=50)
	correo_institucional: EmailStr


class MedicoCreate(MedicoBase):
	pass


class MedicoUpdate(CatalogSchema):
	nombres: str | None = Field(default=None, min_length=2, max_length=100)
	apellidos: str | None = Field(default=None, min_length=2, max_length=100)
	numero_registro: str | None = Field(default=None, min_length=5, max_length=50)
	correo_institucional: EmailStr | None = None


class MedicoResponse(MedicoBase):
	medico_id: UUID
	activo: bool
	creado_en: datetime


class MedicoEspecialidadCreate(CatalogSchema):
	medico_id: UUID
	especialidad_id: UUID
	es_principal: bool = False


class MedicoEspecialidadResponse(CatalogSchema):
	medico_especialidad_id: UUID
	medico_id: UUID
	especialidad_id: UUID
	es_principal: bool


class SedeBase(CatalogSchema):
	nombre: str = Field(min_length=3, max_length=100)
	direccion: str = Field(min_length=5, max_length=200)
	ciudad: str = Field(min_length=2, max_length=100)
	telefono: str | None = None


class SedeCreate(SedeBase):
	pass


class SedeUpdate(CatalogSchema):
	nombre: str | None = Field(default=None, min_length=3, max_length=100)
	direccion: str | None = Field(default=None, min_length=5, max_length=200)
	ciudad: str | None = Field(default=None, min_length=2, max_length=100)
	telefono: str | None = None


class SedeResponse(SedeBase):
	sede_id: UUID
	activo: bool
	creado_en: datetime


class DisponibilidadBase(CatalogSchema):
	medico_id: UUID
	especialidad_id: UUID
	sede_id: UUID
	dia_semana: int
	hora_inicio: time
	hora_fin: time

	@field_validator("dia_semana")
	@classmethod
	def validar_dia_semana(cls, value: int) -> int:
		"""Valida que el dia este entre 1 (lunes) y 7 (domingo)."""
		if value < 1 or value > 7:
			raise ValueError("dia_semana debe estar entre 1 y 7")
		return value

	@field_validator("hora_fin")
	@classmethod
	def validar_hora_fin_mayor_inicio(cls, value: time, info) -> time:
		"""Valida que la hora de fin sea posterior a la hora de inicio."""
		hora_inicio = info.data.get("hora_inicio")
		if hora_inicio is not None and value <= hora_inicio:
			raise ValueError("hora_fin debe ser mayor que hora_inicio")
		return value


class DisponibilidadCreate(DisponibilidadBase):
	pass


class DisponibilidadUpdate(CatalogSchema):
	medico_id: UUID | None = None
	especialidad_id: UUID | None = None
	sede_id: UUID | None = None
	dia_semana: int | None = None
	hora_inicio: time | None = None
	hora_fin: time | None = None

	@field_validator("dia_semana")
	@classmethod
	def validar_dia_semana(cls, value: int | None) -> int | None:
		"""Valida que el dia este entre 1 (lunes) y 7 (domingo)."""
		if value is not None and (value < 1 or value > 7):
			raise ValueError("dia_semana debe estar entre 1 y 7")
		return value

	@field_validator("hora_fin")
	@classmethod
	def validar_hora_fin_mayor_inicio(cls, value: time | None, info) -> time | None:
		"""Si se envian ambas horas, valida que fin sea mayor a inicio."""
		hora_inicio = info.data.get("hora_inicio")
		if value is not None and hora_inicio is not None and value <= hora_inicio:
			raise ValueError("hora_fin debe ser mayor que hora_inicio")
		return value


class DisponibilidadResponse(DisponibilidadBase):
	disponibilidad_id: UUID
	activo: bool
	creado_en: datetime
