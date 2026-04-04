from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# Conjuntos permitidos para validaciones de negocio.
TIPOS_DOCUMENTO_VALIDOS = {"CC", "CE", "PA", "TI"}
TIPOS_SANGRE_VALIDOS = {"A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"}
TIPOS_AFILIACION_VALIDOS = {"cotizante", "beneficiario", "subsidiado"}


class UserBase(BaseModel):
	"""Campos base del perfil de usuario."""

	nombres: str = Field(min_length=2, max_length=100)
	apellidos: str = Field(min_length=2, max_length=100)
	tipo_documento: str
	numero_documento: str = Field(min_length=5, max_length=20)
	fecha_nacimiento: date
	telefono: str | None = Field(default=None, max_length=20)
	correo: EmailStr

	@field_validator("tipo_documento")
	@classmethod
	def validar_tipo_documento(cls, value: str) -> str:
		"""Valida y normaliza el tipo de documento permitido."""
		tipo_documento = value.strip().upper()
		if tipo_documento not in TIPOS_DOCUMENTO_VALIDOS:
			raise ValueError("tipo_documento invalido. Use: CC, CE, PA, TI")
		return tipo_documento

	@field_validator("telefono")
	@classmethod
	def limpiar_telefono(cls, value: str | None) -> str | None:
		"""Limpia espacios del telefono cuando se envia el campo."""
		if value is None:
			return None
		return value.strip()

	model_config = {
		"json_schema_extra": {
			"example": {
				"nombres": "Juan",
				"apellidos": "Perez",
				"tipo_documento": "CC",
				"numero_documento": "1030123456",
				"fecha_nacimiento": "1995-06-10",
				"telefono": "+573001112233",
				"correo": "juan.perez@correo.com",
			}
		}
	}


class UserCreate(UserBase):
	"""Payload para crear el perfil de usuario despues del registro."""

	usuario_id: UUID

	model_config = {
		"json_schema_extra": {
			"example": {
				"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
				"nombres": "Juan",
				"apellidos": "Perez",
				"tipo_documento": "CC",
				"numero_documento": "1030123456",
				"fecha_nacimiento": "1995-06-10",
				"telefono": "+573001112233",
				"correo": "juan.perez@correo.com",
			}
		}
	}


class UserUpdate(BaseModel):
	"""Payload para actualizacion parcial de datos personales."""

	nombres: str | None = Field(default=None, min_length=2, max_length=100)
	apellidos: str | None = Field(default=None, min_length=2, max_length=100)
	tipo_documento: str | None = None
	numero_documento: str | None = Field(default=None, min_length=5, max_length=20)
	fecha_nacimiento: date | None = None
	telefono: str | None = Field(default=None, max_length=20)
	correo: EmailStr | None = None

	@field_validator("tipo_documento")
	@classmethod
	def validar_tipo_documento(cls, value: str | None) -> str | None:
		"""Valida tipo de documento cuando el campo es enviado."""
		if value is None:
			return None
		tipo_documento = value.strip().upper()
		if tipo_documento not in TIPOS_DOCUMENTO_VALIDOS:
			raise ValueError("tipo_documento invalido. Use: CC, CE, PA, TI")
		return tipo_documento

	@field_validator("telefono")
	@classmethod
	def limpiar_telefono(cls, value: str | None) -> str | None:
		"""Limpia espacios del telefono cuando se envia el campo."""
		if value is None:
			return None
		return value.strip()

	model_config = {
		"json_schema_extra": {
			"example": {
				"telefono": "+573007778899",
				"correo": "nuevo.correo@correo.com",
			}
		}
	}


class UserResponse(UserBase):
	"""Respuesta estandar del recurso usuario."""

	usuario_id: UUID
	creado_en: datetime
	actualizado_en: datetime

	model_config = {
		"from_attributes": True,
		"json_schema_extra": {
			"example": {
				"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
				"nombres": "Juan",
				"apellidos": "Perez",
				"tipo_documento": "CC",
				"numero_documento": "1030123456",
				"fecha_nacimiento": "1995-06-10",
				"telefono": "+573001112233",
				"correo": "juan.perez@correo.com",
				"creado_en": "2026-04-02T13:20:00Z",
				"actualizado_en": "2026-04-02T13:20:00Z",
			}
		}
	}


class UserLookupResponse(BaseModel):
	"""Respuesta resumida para busquedas de usuario por documento."""

	usuario_id: UUID
	correo: EmailStr
	nombres: str
	apellidos: str

	model_config = {
		"from_attributes": True,
		"json_schema_extra": {
			"example": {
				"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
				"correo": "juan.perez@correo.com",
				"nombres": "Juan",
				"apellidos": "Perez",
			}
		}
	}


class MedicalInfoBase(BaseModel):
	"""Campos base de informacion medica del usuario."""

	tipo_sangre: str | None = None
	alergias: str | None = None
	enfermedades_cronicas: str | None = None
	medicamentos_actuales: str | None = None

	@field_validator("tipo_sangre")
	@classmethod
	def validar_tipo_sangre(cls, value: str | None) -> str | None:
		"""Valida tipo de sangre cuando el campo es enviado."""
		if value is None:
			return None
		tipo_sangre = value.strip().upper()
		if tipo_sangre not in TIPOS_SANGRE_VALIDOS:
			raise ValueError("tipo_sangre invalido. Use: A+, A-, B+, B-, O+, O-, AB+, AB-")
		return tipo_sangre

	model_config = {
		"json_schema_extra": {
			"example": {
				"tipo_sangre": "O+",
				"alergias": "Penicilina",
				"enfermedades_cronicas": "Hipertension",
				"medicamentos_actuales": "Losartan 50mg",
			}
		}
	}


class MedicalInfoCreate(MedicalInfoBase):
	"""Payload para crear o actualizar informacion medica."""


class MedicalInfoResponse(MedicalInfoBase):
	"""Respuesta estandar de informacion medica."""

	info_medica_id: UUID
	usuario_id: UUID
	actualizado_en: datetime

	model_config = {
		"from_attributes": True,
		"json_schema_extra": {
			"example": {
				"info_medica_id": "4df5a6c5-d035-4f61-a0fd-95a9e0834558",
				"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
				"tipo_sangre": "O+",
				"alergias": "Penicilina",
				"enfermedades_cronicas": "Hipertension",
				"medicamentos_actuales": "Losartan 50mg",
				"actualizado_en": "2026-04-02T13:20:00Z",
			}
		}
	}


class AfiliacionBase(BaseModel):
	"""Campos base de afiliacion del usuario."""

	tipo_afiliacion: str
	numero_poliza: str = Field(min_length=5, max_length=50)
	fecha_afiliacion: date
	medico_asignado_id: UUID | None = None

	@field_validator("tipo_afiliacion")
	@classmethod
	def validar_tipo_afiliacion(cls, value: str) -> str:
		"""Valida y normaliza tipo de afiliacion permitido."""
		tipo_afiliacion = value.strip().lower()
		if tipo_afiliacion not in TIPOS_AFILIACION_VALIDOS:
			raise ValueError("tipo_afiliacion invalido. Use: cotizante, beneficiario, subsidiado")
		return tipo_afiliacion

	model_config = {
		"json_schema_extra": {
			"example": {
				"tipo_afiliacion": "cotizante",
				"numero_poliza": "POL-2026-0001",
				"fecha_afiliacion": "2026-04-01",
				"medico_asignado_id": "fc18bf77-a69f-4a0e-b1b7-05cc924e48d2",
			}
		}
	}


class AfiliacionCreate(AfiliacionBase):
	"""Payload para crear o actualizar afiliacion."""


class AfiliacionResponse(AfiliacionBase):
	"""Respuesta estandar de afiliacion."""

	afiliacion_id: UUID
	usuario_id: UUID
	estado: str
	creado_en: datetime
	actualizado_en: datetime

	model_config = {
		"from_attributes": True,
		"json_schema_extra": {
			"example": {
				"afiliacion_id": "bc8ea9b3-b53f-4f1f-a314-f2272f5f0dfe",
				"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
				"tipo_afiliacion": "cotizante",
				"numero_poliza": "POL-2026-0001",
				"fecha_afiliacion": "2026-04-01",
				"medico_asignado_id": "fc18bf77-a69f-4a0e-b1b7-05cc924e48d2",
				"estado": "activo",
				"creado_en": "2026-04-02T13:20:00Z",
				"actualizado_en": "2026-04-02T13:20:00Z",
			}
		}
	}


class UsuarioCompletoResponse(BaseModel):
	"""Respuesta agregada para consultar todo el perfil en una sola llamada."""

	user: UserResponse
	informacion_medica: MedicalInfoResponse | None
	afiliacion: AfiliacionResponse | None

	model_config = {
		"from_attributes": True,
		"json_schema_extra": {
			"example": {
				"user": {
					"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
					"nombres": "Juan",
					"apellidos": "Perez",
					"tipo_documento": "CC",
					"numero_documento": "1030123456",
					"fecha_nacimiento": "1995-06-10",
					"telefono": "+573001112233",
					"correo": "juan.perez@correo.com",
					"creado_en": "2026-04-02T13:20:00Z",
					"actualizado_en": "2026-04-02T13:20:00Z",
				},
				"informacion_medica": {
					"info_medica_id": "4df5a6c5-d035-4f61-a0fd-95a9e0834558",
					"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
					"tipo_sangre": "O+",
					"alergias": "Penicilina",
					"enfermedades_cronicas": "Hipertension",
					"medicamentos_actuales": "Losartan 50mg",
					"actualizado_en": "2026-04-02T13:20:00Z",
				},
				"afiliacion": {
					"afiliacion_id": "bc8ea9b3-b53f-4f1f-a314-f2272f5f0dfe",
					"usuario_id": "8b4dd5d0-90ec-4a05-bf31-4cf6fd9f5347",
					"tipo_afiliacion": "cotizante",
					"numero_poliza": "POL-2026-0001",
					"fecha_afiliacion": "2026-04-01",
					"medico_asignado_id": "fc18bf77-a69f-4a0e-b1b7-05cc924e48d2",
					"estado": "activo",
					"creado_en": "2026-04-02T13:20:00Z",
					"actualizado_en": "2026-04-02T13:20:00Z",
				},
			}
		}
	}
