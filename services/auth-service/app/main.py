"""API principal del Auth Service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware

from app.auth import (
	DocumentoNoEncontradoError,
	UserServiceUnavailableError,
	autenticar_usuario,
	configurar_2fa,
	crear_token_recuperacion,
	generar_tokens_para_credencial,
	get_correo_by_documento,
	get_credencial_by_correo,
	get_credencial_by_id,
	refresh_access_token,
	registrar_usuario,
	resetear_password,
	verificar_codigo_2fa,
	verify_jwt_token,
)
from app.rabbitmq_client import publicar_evento
from app.database import Base, engine, get_db
from app.core.logger import setup_logger, log_event
from app.core.error_handler import register_exception_handlers
from app.schemas import (
	Enable2FARequest,
	LoginResponse,
	MessageResponse,
	RegisterResponse,
	RecoverRequest,
	RefreshTokenRequest,
	ResetPasswordRequest,
	TokenResponse,
	UserLogin,
	UserLoginDocumento,
	UserRegister,
	Verify2FARequest,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
	"""Gestiona eventos de ciclo de vida de la aplicacion."""
	setup_logger()
	log_event("MAIN", "INIT", "info", "Iniciando Auth Service...")
	Base.metadata.create_all(bind=engine)
	log_event("MAIN", "INIT", "info", "Base de datos inicializada")
	log_event("MAIN", "INIT", "info", "Auth Service listo")
	yield
	log_event("MAIN", "SHUTDOWN", "info", "Auth Service finalizando")


app = FastAPI(
	title="EPS Digital - Auth Service",
	version="1.0.0",
	description="Servicio de autenticacion y gestion de sesiones.",
	lifespan=lifespan,
)

register_exception_handlers(app)

origins = [
    "https://eps-digital-cn2h.onrender.com",
    "https://eps-digital-cn2h.onrender.com/",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5173/",
    "http://127.0.0.1:5173/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-User-ID"],
	max_age=600,
)

security = HTTPBearer(auto_error=False)


def _extract_bearer_token(
	credentials: HTTPAuthorizationCredentials | None,
) -> str:
	if credentials is None or credentials.scheme.lower() != "bearer":
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Token Bearer requerido",
		)
	return credentials.credentials


def _get_credencial_id_from_access_token(token: str) -> UUID:
	try:
		payload = verify_jwt_token(token, expected_tipo="access")
		return UUID(payload["sub"])
	except (ValueError, KeyError) as exc:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Token invalido o expirado",
		) from exc


@app.post(
	"/auth/register",
	response_model=RegisterResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Usuario registrado correctamente",
			"content": {
				"application/json": {
					"example": {
						"message": "Usuario registrado correctamente",
						"success": True,
						"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
					}
				}
			},
		},
		400: {
			"description": "Error de validacion de negocio",
			"content": {"application/json": {"example": {"detail": "El correo ya esta registrado"}}},
		},
	},
)
def register(
	payload: UserRegister,
	request: Request,
	db: Session = Depends(get_db),
) -> dict:
	log_event("AUTH", "REGISTER", "info", f"Registro solicitado para correo={payload.correo}")
	try:
		credencial = registrar_usuario(
			db,
			payload,
			ip=request.client.host if request.client else None,
			user_agent=request.headers.get("user-agent"),
		)

		publicar_evento(
			evento="cuenta_creada",
			payload={
				"evento": "cuenta_creada",
				"email": credencial.correo,
				"nombre": credencial.correo.split("@")[0],
			},
		)

		log_event("AUTH", "REGISTER", "info", f"Registro exitoso: usuario_id={credencial.usuario_id}")
		return {
			"message": "Usuario registrado correctamente",
			"success": True,
			"usuario_id": str(credencial.usuario_id),
		}
	except ValueError as exc:
		log_event("AUTH", "REGISTER", "warning", f"Registro fallido: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post(
	"/auth/login",
	response_model=LoginResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Resultado de autenticacion",
			"content": {
				"application/json": {
					"example": {
						"access_token": "",
						"refresh_token": "",
						"token_type": "bearer",
						"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
						"requiere_2fa": True,
					}
				}
			},
		},
		401: {
			"description": "Credenciales invalidas o cuenta bloqueada",
			"content": {"application/json": {"example": {"detail": "Credenciales invalidas"}}},
		},
	},
)
def login(
	payload: UserLogin,
	request: Request,
	db: Session = Depends(get_db),
) -> LoginResponse:
	log_event("AUTH", "LOGIN", "info", f"Login solicitado para correo={payload.correo}")
	try:
		credencial_id, tiene_2fa = autenticar_usuario(
			db,
			payload.correo,
			payload.password,
			ip=request.client.host if request.client else None,
			user_agent=request.headers.get("user-agent"),
		)
	except ValueError as exc:
		log_event("AUTH", "LOGIN", "warning", f"Login fallido para correo={payload.correo}: {exc}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

	credencial = get_credencial_by_id(db, credencial_id)
	if not credencial:
		log_event("AUTH", "LOGIN", "error", f"Credencial no valida para id={credencial_id}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial no valida")

	if tiene_2fa:
		log_event("AUTH", "LOGIN", "info", f"2FA requerido para credencial_id={credencial_id}")
		return LoginResponse(
			access_token="",
			refresh_token="",
			token_type="bearer",
			usuario_id=credencial.usuario_id,
			requiere_2fa=True,
			rol=credencial.rol,
		)

	access_token, refresh_token = generar_tokens_para_credencial(credencial_id)
	log_event("AUTH", "LOGIN", "info", f"Login exitoso: credencial_id={credencial_id}, rol={credencial.rol}")
	return LoginResponse(
		access_token=access_token,
		refresh_token=refresh_token,
		token_type="bearer",
		usuario_id=credencial.usuario_id,
		requiere_2fa=False,
		rol=credencial.rol,
	)


@app.post(
	"/auth/login/documento",
	response_model=LoginResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Resultado de autenticacion por documento",
			"content": {
				"application/json": {
					"example": {
						"access_token": "",
						"refresh_token": "",
						"token_type": "bearer",
						"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
						"requiere_2fa": True,
					}
				}
			},
		},
		401: {
			"description": "Credenciales invalidas o cuenta bloqueada",
			"content": {"application/json": {"example": {"detail": "Credenciales invalidas"}}},
		},
		503: {
			"description": "User Service no disponible",
			"content": {
				"application/json": {
					"example": {
						"detail": "No fue posible validar el documento en este momento"
					}
				}
			},
		},
	},
)
def login_documento(
	payload: UserLoginDocumento,
	request: Request,
	db: Session = Depends(get_db),
) -> LoginResponse:
	log_event("AUTH", "LOGIN_DOC", "info", f"Login por documento: tipo={payload.tipo_documento}, numero={payload.numero_documento}")
	try:
		correo = get_correo_by_documento(db, payload.tipo_documento, payload.numero_documento)
	except DocumentoNoEncontradoError:
		log_event("AUTH", "LOGIN_DOC", "warning", f"Documento no encontrado: {payload.tipo_documento}-{payload.numero_documento}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Credenciales invalidas",
		)
	except UserServiceUnavailableError as exc:
		log_event("AUTH", "LOGIN_DOC", "error", f"User Service no disponible: {exc}")
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="No fue posible validar el documento en este momento",
		) from exc
	except ValueError as exc:
		log_event("AUTH", "LOGIN_DOC", "warning", f"Error validando documento: {exc}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

	try:
		credencial_id, tiene_2fa = autenticar_usuario(
			db,
			correo,
			payload.password,
			ip=request.client.host if request.client else None,
			user_agent=request.headers.get("user-agent"),
		)
	except ValueError as exc:
		log_event("AUTH", "LOGIN_DOC", "warning", f"Login fallido para correo={correo}: {exc}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

	credencial = get_credencial_by_id(db, credencial_id)
	if not credencial:
		log_event("AUTH", "LOGIN_DOC", "error", f"Credencial no valida para id={credencial_id}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial no valida")

	if tiene_2fa:
		log_event("AUTH", "LOGIN_DOC", "info", f"2FA requerido para credencial_id={credencial_id}")
		return LoginResponse(
			access_token="",
			refresh_token="",
			token_type="bearer",
			usuario_id=credencial.usuario_id,
			requiere_2fa=True,
			rol=credencial.rol,
		)

	access_token, refresh_token = generar_tokens_para_credencial(credencial_id)
	log_event("AUTH", "LOGIN_DOC", "info", f"Login por documento exitoso: credencial_id={credencial_id}")
	return LoginResponse(
		access_token=access_token,
		refresh_token=refresh_token,
		token_type="bearer",
		usuario_id=credencial.usuario_id,
		requiere_2fa=False,
		rol=credencial.rol,
	)


@app.post(
	"/auth/refresh",
	response_model=TokenResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Token renovado correctamente",
			"content": {
				"application/json": {
					"example": {
						"access_token": "nuevo_access_token",
						"refresh_token": "refresh_token_actual",
						"token_type": "bearer",
					}
				}
			},
		},
		401: {
			"description": "Refresh token invalido o expirado",
			"content": {
				"application/json": {
					"example": {"detail": "Token JWT invalido o expirado"}
				}
			},
		},
	},
)
def refresh(
	payload: RefreshTokenRequest,
	db: Session = Depends(get_db),
) -> TokenResponse:
	log_event("AUTH", "REFRESH", "info", "Refresh token solicitado")
	try:
		new_access_token = refresh_access_token(db, payload.refresh_token)
		log_event("AUTH", "REFRESH", "info", "Token renovado correctamente")
		return TokenResponse(
			access_token=new_access_token,
			refresh_token=payload.refresh_token,
			token_type="bearer",
		)
	except ValueError as exc:
		log_event("AUTH", "REFRESH", "warning", f"Refresh fallido: {exc}")
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@app.post(
	"/auth/verify-2fa",
	tags=["auth"],
	responses={
		200: {
			"description": "Codigo 2FA verificado",
			"content": {
				"application/json": {
					"example": {
						"access_token": "access_token",
						"refresh_token": "refresh_token",
						"token_type": "bearer",
						"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
					}
				}
			},
		},
		401: {
			"description": "Codigo 2FA invalido o expirado",
			"content": {"application/json": {"example": {"detail": "Codigo 2FA invalido o expirado"}}},
		},
	},
)
def verify_2fa(
	payload: Verify2FARequest,
	request: Request,
	db: Session = Depends(get_db),
) -> dict:
	log_event("AUTH", "VERIFY_2FA", "info", f"Verificacion 2FA solicitada para credencial_id={payload.credencial_id}")
	is_valid = verificar_codigo_2fa(
		db,
		payload.credencial_id,
		payload.codigo,
		ip=request.client.host if request.client else None,
		user_agent=request.headers.get("user-agent"),
	)
	if not is_valid:
		log_event("AUTH", "VERIFY_2FA", "warning", f"2FA invalido para credencial_id={payload.credencial_id}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Codigo 2FA invalido o expirado",
		)

	credencial = get_credencial_by_id(db, payload.credencial_id)
	if not credencial:
		log_event("AUTH", "VERIFY_2FA", "error", f"Credencial no encontrada: {payload.credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	access_token, refresh_token = generar_tokens_para_credencial(payload.credencial_id)
	log_event("AUTH", "VERIFY_2FA", "info", f"2FA verificado, tokens generados para credencial_id={payload.credencial_id}")
	return {
		"access_token": access_token,
		"refresh_token": refresh_token,
		"token_type": "bearer",
		"usuario_id": str(credencial.usuario_id),
		"rol": credencial.rol,
	}


@app.post(
	"/auth/enable-2fa",
	response_model=MessageResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "2FA habilitado",
			"content": {
				"application/json": {
					"example": {
						"message": "2FA habilitado correctamente",
						"success": True,
					}
				}
			},
		},
		401: {
			"description": "Token o codigo invalido",
			"content": {
				"application/json": {
					"example": {"detail": "Codigo 2FA invalido o expirado"}
				}
			},
		},
	},
)
def enable_2fa(
	payload: Enable2FARequest,
	request: Request,
	credentials: HTTPAuthorizationCredentials | None = Depends(security),
	db: Session = Depends(get_db),
) -> MessageResponse:
	token = _extract_bearer_token(credentials)
	credencial_id = _get_credencial_id_from_access_token(token)
	log_event("AUTH", "ENABLE_2FA", "info", f"Habilitar 2FA solicitado para credencial_id={credencial_id}")

	is_valid = verificar_codigo_2fa(
		db,
		credencial_id,
		payload.codigo,
		ip=request.client.host if request.client else None,
		user_agent=request.headers.get("user-agent"),
	)
	if not is_valid:
		log_event("AUTH", "ENABLE_2FA", "warning", f"2FA invalido para habilitar: credencial_id={credencial_id}")
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Codigo 2FA invalido o expirado",
		)

	enabled = configurar_2fa(db, credencial_id, habilitar=True)
	if not enabled:
		log_event("AUTH", "ENABLE_2FA", "error", f"Credencial no encontrada: {credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	log_event("AUTH", "ENABLE_2FA", "info", f"2FA habilitado para credencial_id={credencial_id}")
	return MessageResponse(message="2FA habilitado correctamente", success=True)


@app.post(
	"/auth/recover",
	response_model=MessageResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Solicitud de recuperacion procesada",
			"content": {
				"application/json": {
					"example": {
						"message": "Si el correo existe, se envio el proceso de recuperacion",
						"success": True,
					}
				}
			},
		}
	},
)
def recover(
	payload: RecoverRequest,
	db: Session = Depends(get_db),
) -> MessageResponse:
	log_event("AUTH", "RECOVER", "info", f"Recuperacion solicitada para correo={payload.correo}")
	credencial = get_credencial_by_correo(db, payload.correo)
	if credencial:
		crear_token_recuperacion(db, credencial.credencial_id)
		log_event("AUTH", "RECOVER", "info", f"Token de recuperacion creado para credencial_id={credencial.credencial_id}")
	else:
		log_event("AUTH", "RECOVER", "warning", f"Correo no encontrado: {payload.correo}")

	return MessageResponse(
		message="Si el correo existe, se envio el proceso de recuperacion",
		success=True,
	)


@app.post(
	"/auth/reset-password",
	response_model=MessageResponse,
	tags=["auth"],
	responses={
		200: {
			"description": "Contrasena actualizada",
			"content": {
				"application/json": {
					"example": {
						"message": "Contrasena actualizada correctamente",
						"success": True,
					}
				}
			},
		},
		400: {
			"description": "Token invalido o datos incorrectos",
			"content": {"application/json": {"example": {"detail": "Token invalido o expirado"}}},
		},
	},
)
def reset_password(
	payload: ResetPasswordRequest,
	db: Session = Depends(get_db),
) -> MessageResponse:
	log_event("AUTH", "RESET_PWD", "info", "Reset de password solicitado")
	if payload.new_password != payload.confirm_new_password:
		log_event("AUTH", "RESET_PWD", "warning", "confirm_new_password no coincide")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="confirm_new_password no coincide con new_password",
		)

	ok = resetear_password(db, payload.token, payload.new_password)
	if not ok:
		log_event("AUTH", "RESET_PWD", "warning", "Token invalido o expirado para reset")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalido o expirado")

	log_event("AUTH", "RESET_PWD", "info", "Password reseteado correctamente")
	return MessageResponse(message="Contrasena actualizada correctamente", success=True)


@app.get(
	"/auth/me",
	tags=["auth"],
	responses={
		200: {
			"description": "Informacion de la credencial autenticada",
			"content": {
				"application/json": {
					"example": {
						"credencial_id": "550e8400-e29b-41d4-a716-446655440000",
						"correo": "laura.gomez@correo.com",
						"rol": "usuario",
						"activo": True,
						"tiene_2fa": False,
					}
				}
			},
		},
		401: {
			"description": "Token invalido o expirado",
			"content": {
				"application/json": {
					"example": {"detail": "Token invalido o expirado"}
				}
			},
		},
	},
)
def me(
	credentials: HTTPAuthorizationCredentials | None = Depends(security),
	db: Session = Depends(get_db),
) -> dict:
	token = _extract_bearer_token(credentials)
	credencial_id = _get_credencial_id_from_access_token(token)
	log_event("AUTH", "ME", "info", f"Consulta /me para credencial_id={credencial_id}")
	credencial = get_credencial_by_id(db, credencial_id)

	if not credencial:
		log_event("AUTH", "ME", "warning", f"Credencial no encontrada: {credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	return {
		"credencial_id": str(credencial.credencial_id),
		"correo": credencial.correo,
		"rol": credencial.rol,
		"activo": credencial.activo,
		"tiene_2fa": credencial.tiene_2fa,
	}


@app.get(
	"/auth/perfil",
	tags=["auth"],
	responses={
		200: {
			"description": "Perfil basico del usuario autenticado",
			"content": {
				"application/json": {
					"example": {
						"usuario_id": "550e8400-e29b-41d4-a716-446655440000",
						"rol": "admin",
					}
				}
			},
		},
		401: {
			"description": "Token invalido o expirado",
		},
	},
)
def obtener_perfil(
	credentials: HTTPAuthorizationCredentials | None = Depends(security),
	db: Session = Depends(get_db),
) -> dict:
	token = _extract_bearer_token(credentials)
	credencial_id = _get_credencial_id_from_access_token(token)
	log_event("AUTH", "PERFIL", "info", f"Consulta perfil para credencial_id={credencial_id}")
	credencial = get_credencial_by_id(db, credencial_id)

	if not credencial:
		log_event("AUTH", "PERFIL", "warning", f"Credencial no encontrada: {credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	return {
		"usuario_id": str(credencial.usuario_id),
		"rol": credencial.rol,
	}


@app.get(
	"/auth/medico-id",
	tags=["auth"],
	responses={
		200: {
			"description": "ID del medico asociado al usuario autenticado",
			"content": {
				"application/json": {
					"example": {
						"medico_id": "550e8400-e29b-41d4-a716-446655440000",
					}
				}
			},
		},
		401: {
			"description": "Token invalido o expirado",
		},
		404: {
			"description": "Usuario no tiene medico asociado",
		},
	},
)
def obtener_medico_id(
	credentials: HTTPAuthorizationCredentials | None = Depends(security),
	db: Session = Depends(get_db),
) -> dict:
	token = _extract_bearer_token(credentials)
	credencial_id = _get_credencial_id_from_access_token(token)
	log_event("AUTH", "MEDICO_ID", "info", f"Consulta medico_id para credencial_id={credencial_id}")
	credencial = get_credencial_by_id(db, credencial_id)

	if not credencial:
		log_event("AUTH", "MEDICO_ID", "warning", f"Credencial no encontrada: {credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	if not credencial.medico_id:
		log_event("AUTH", "MEDICO_ID", "warning", f"Usuario sin medico asociado: credencial_id={credencial_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no tiene medico asociado")

	log_event("AUTH", "MEDICO_ID", "info", f"medico_id={credencial.medico_id} para credencial_id={credencial_id}")
	return {
		"medico_id": str(credencial.medico_id),
	}
