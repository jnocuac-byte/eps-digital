"""Esquemas Pydantic para validacion de entradas y salidas del Auth Service."""
from datetime import date
import re
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ValidationInfo, field_validator


TIPOS_DOCUMENTO_VALIDOS = {"CC", "CE", "PA", "TI"}
CODIGO_2FA_PATTERN = r"^\d{6}$"


class UserRegister(BaseModel):
	"""Schema de entrada para registro de usuario."""

	# Nombres del usuario.
	nombres: str = Field(..., min_length=2, max_length=100)
	# Apellidos del usuario.
	apellidos: str = Field(..., min_length=2, max_length=100)
	# Tipo de documento permitido: CC, CE, PA o TI.
	tipo_documento: str = Field(...)
	# Numero de documento de identidad.
	numero_documento: str = Field(..., min_length=5, max_length=20)
	# Fecha de nacimiento en formato ISO (YYYY-MM-DD).
	fecha_nacimiento: date
	# Correo electronico del usuario.
	correo: EmailStr
	# Telefono de contacto (opcional).
	telefono: str | None = None
	# Contrasena en texto plano para validacion inicial.
	password: str = Field(..., min_length=8)
	# Confirmacion de contrasena; debe coincidir con password.
	confirm_password: str
	# Confirmacion explicita de aceptacion de terminos y condiciones.
	acepta_terminos: bool

	model_config = {
		"json_schema_extra": {
			"example": {
				"nombres": "Laura",
				"apellidos": "Gomez",
				"tipo_documento": "CC",
				"numero_documento": "1020304050",
				"fecha_nacimiento": "1995-08-14",
				"correo": "laura.gomez@correo.com",
				"telefono": "3001234567",
				"password": "ClaveSegura1",
				"confirm_password": "ClaveSegura1",
				"acepta_terminos": True,
			}
		}
	}

	@field_validator("tipo_documento")
	@classmethod
	def validar_tipo_documento(cls, value: str) -> str:
		"""Valida que el tipo de documento este dentro de las opciones permitidas."""
		if value not in TIPOS_DOCUMENTO_VALIDOS:
			raise ValueError("tipo_documento debe ser uno de: CC, CE, PA, TI")
		return value

	@field_validator("password")
	@classmethod
	def validar_password_segura(cls, value: str) -> str:
		"""Valida minimo una mayuscula y un numero en la contrasena."""
		if not re.search(r"[A-Z]", value):
			raise ValueError("La contrasena debe contener al menos una letra mayuscula")
		if not re.search(r"\d", value):
			raise ValueError("La contrasena debe contener al menos un numero")
		return value

	@field_validator("confirm_password")
	@classmethod
	def validar_confirm_password(cls, value: str, info: ValidationInfo) -> str:
		"""Valida que la confirmacion de contrasena coincida con password."""
		password = info.data.get("password") if info.data else None
		if password is not None and value != password:
			raise ValueError("confirm_password no coincide con password")
		return value

	@field_validator("acepta_terminos")
	@classmethod
	def validar_acepta_terminos(cls, value: bool) -> bool:
		"""Valida que el usuario acepte terminos y condiciones."""
		if value is not True:
			raise ValueError("Debe aceptar terminos y condiciones")
		return value

class UserLogin(BaseModel):
	"""Schema de entrada para autenticacion de usuario."""

	# Correo electronico del usuario.
	correo: EmailStr
	# Contrasena del usuario.
	password: str

	model_config = {
		"json_schema_extra": {
			"example": {
				"correo": "laura.gomez@correo.com",
				"password": "ClaveSegura1",
			}
		}
	}


class TokenResponse(BaseModel):
	"""Respuesta basica con tokens de autenticacion."""

	# Token JWT de acceso.
	access_token: str
	# Token JWT de refresco.
	refresh_token: str
	# Tipo de token utilizado por la API.
	token_type: str = "bearer"

	model_config = {
		"json_schema_extra": {
			"example": {
				"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
				"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
				"token_type": "bearer",
			}
		}
	}


class RefreshTokenRequest(BaseModel):
	"""Schema para solicitar renovacion de token de acceso."""

	# Token de refresco valido.
	refresh_token: str

	model_config = {
		"json_schema_extra": {
			"example": {
				"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
			}
		}
	}


class RecoverRequest(BaseModel):
	"""Schema para solicitar inicio de recuperacion de contrasena."""

	# Correo asociado a la cuenta.
	correo: EmailStr

	model_config = {
		"json_schema_extra": {
			"example": {
				"correo": "laura.gomez@correo.com",
			}
		}
	}


class ResetPasswordRequest(BaseModel):
	"""Schema para restablecer contrasena mediante token de recuperacion."""

	# Token de recuperacion (hash o token firmado).
	token: str
	# Nueva contrasena propuesta.
	new_password: str = Field(..., min_length=8)
	# Confirmacion de nueva contrasena.
	confirm_new_password: str

	model_config = {
		"json_schema_extra": {
			"example": {
				"token": "f1a5f96f0f7c4f20a238f99fdb7f0cda",
				"new_password": "NuevaClave1",
				"confirm_new_password": "NuevaClave1",
			}
		}
	}

	@field_validator("new_password")
	@classmethod
	def validar_new_password_segura(cls, value: str) -> str:
		"""Valida minimo una mayuscula y un numero en la nueva contrasena."""
		if not re.search(r"[A-Z]", value):
			raise ValueError("La contrasena debe contener al menos una letra mayuscula")
		if not re.search(r"\d", value):
			raise ValueError("La contrasena debe contener al menos un numero")
		return value

	@field_validator("confirm_new_password")
	@classmethod
	def validar_confirm_new_password(cls, value: str, info: ValidationInfo) -> str:
		"""Valida que la confirmacion coincida con la nueva contrasena."""
		new_password = info.data.get("new_password") if info.data else None
		if new_password is not None and value != new_password:
			raise ValueError("confirm_new_password no coincide con new_password")
		return value


class Verify2FARequest(BaseModel):
	"""Schema para verificar codigo de segundo factor."""

	# Identificador de la credencial 2FA (UUID).
	credencial_id: UUID
	# Codigo OTP de 6 digitos.
	codigo: str = Field(..., pattern=CODIGO_2FA_PATTERN)

	model_config = {
		"json_schema_extra": {
			"example": {
				"credencial_id": "550e8400-e29b-41d4-a716-446655440000",
				"codigo": "123456",
			}
		}
	}


class Enable2FARequest(BaseModel):
	"""Schema para activar 2FA luego de verificar un codigo OTP."""

	# Codigo OTP de 6 digitos para confirmar activacion.
	codigo: str = Field(..., pattern=CODIGO_2FA_PATTERN)

	model_config = {
		"json_schema_extra": {
			"example": {
				"codigo": "123456",
			}
		}
	}


class MessageResponse(BaseModel):
	"""Respuesta comun para operaciones exitosas o informativas."""

	# Mensaje descriptivo de la operacion.
	message: str
	# Indica si la operacion fue exitosa.
	success: bool

	model_config = {
		"json_schema_extra": {
			"example": {
				"message": "Operacion realizada correctamente",
				"success": True,
			}
		}
	}

class RegisterResponse(MessageResponse):
    """Respuesta específica para el registro que incluye el ID del usuario."""
    usuario_id: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Usuario registrado correctamente",
                "success": True,
                "usuario_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
    }


class ErrorResponse(BaseModel):
	"""Respuesta estandar de error para la API."""

	# Detalle del error reportado.
	detail: str
	# Codigo de error interno (opcional).
	error_code: str | None = None

	model_config = {
		"json_schema_extra": {
			"example": {
				"detail": "Credenciales invalidas",
				"error_code": "AUTH_001",
			}
		}
	}


class LoginResponse(BaseModel):
	"""Respuesta de login con tokens y estado de 2FA del usuario."""

	# Token JWT de acceso.
	access_token: str
	# Token JWT de refresco.
	refresh_token: str
	# Tipo de token (normalmente bearer).
	token_type: str
	# Identificador unico del usuario autenticado.
	usuario_id: UUID
	# Indica si se debe solicitar verificacion 2FA.
	requiere_2fa: bool

	model_config = {
		"json_schema_extra": {
			"example": {
				"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
				"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
				"token_type": "bearer",
				"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
				"requiere_2fa": True,
			}
		}
	}
