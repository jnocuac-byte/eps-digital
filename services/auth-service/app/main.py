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
from app.database import Base, engine, get_db
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
	Base.metadata.create_all(bind=engine)
	yield


app = FastAPI(
	title="EPS Digital - Auth Service",
	version="1.0.0",
	description="Servicio de autenticacion y gestion de sesiones.",
	lifespan=lifespan,
)

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
    allow_headers=["Authorization", "Content-Type", "Accept"],
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
	try:
		credencial = registrar_usuario(
			db,
			payload,
			ip=request.client.host if request.client else None,
			user_agent=request.headers.get("user-agent"),
		)
		return {
			"message": "Usuario registrado correctamente",
			"success": True,
			"usuario_id": str(credencial.usuario_id),
		}
	except ValueError as exc:
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
	try:
		credencial_id, tiene_2fa = autenticar_usuario(
			db,
			payload.correo,
			payload.password,
			ip=request.client.host if request.client else None,
			user_agent=request.headers.get("user-agent"),
		)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

	credencial = get_credencial_by_id(db, credencial_id)
	if not credencial:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial no valida")

	if tiene_2fa:
		# LoginResponse exige strings; se devuelven vacios cuando 2FA aun no finaliza.
		return LoginResponse(
			access_token="",
			refresh_token="",
			token_type="bearer",
			usuario_id=credencial.usuario_id,
			requiere_2fa=True,
		)

	access_token, refresh_token = generar_tokens_para_credencial(credencial_id)
	return LoginResponse(
		access_token=access_token,
		refresh_token=refresh_token,
		token_type="bearer",
		usuario_id=credencial.usuario_id,
		requiere_2fa=False,
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
	try:
		correo = get_correo_by_documento(db, payload.tipo_documento, payload.numero_documento)
	except DocumentoNoEncontradoError:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Credenciales invalidas",
		)
	except UserServiceUnavailableError as exc:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="No fue posible validar el documento en este momento",
		) from exc
	except ValueError as exc:
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
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

	credencial = get_credencial_by_id(db, credencial_id)
	if not credencial:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credencial no valida")

	if tiene_2fa:
		return LoginResponse(
			access_token="",
			refresh_token="",
			token_type="bearer",
			usuario_id=credencial.usuario_id,
			requiere_2fa=True,
		)

	access_token, refresh_token = generar_tokens_para_credencial(credencial_id)
	return LoginResponse(
		access_token=access_token,
		refresh_token=refresh_token,
		token_type="bearer",
		usuario_id=credencial.usuario_id,
		requiere_2fa=False,
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
	try:
		new_access_token = refresh_access_token(db, payload.refresh_token)
		return TokenResponse(
			access_token=new_access_token,
			refresh_token=payload.refresh_token,
			token_type="bearer",
		)
	except ValueError as exc:
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
	is_valid = verificar_codigo_2fa(
		db,
		payload.credencial_id,
		payload.codigo,
		ip=request.client.host if request.client else None,
		user_agent=request.headers.get("user-agent"),
	)
	if not is_valid:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Codigo 2FA invalido o expirado",
		)

	credencial = get_credencial_by_id(db, payload.credencial_id)
	if not credencial:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	access_token, refresh_token = generar_tokens_para_credencial(payload.credencial_id)
	return {
		"access_token": access_token,
		"refresh_token": refresh_token,
		"token_type": "bearer",
		"usuario_id": str(credencial.usuario_id),
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

	is_valid = verificar_codigo_2fa(
		db,
		credencial_id,
		payload.codigo,
		ip=request.client.host if request.client else None,
		user_agent=request.headers.get("user-agent"),
	)
	if not is_valid:
		raise HTTPException(
			status_code=status.HTTP_401_UNAUTHORIZED,
			detail="Codigo 2FA invalido o expirado",
		)

	enabled = configurar_2fa(db, credencial_id, habilitar=True)
	if not enabled:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

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
	credencial = get_credencial_by_correo(db, payload.correo)
	if credencial:
		crear_token_recuperacion(db, credencial.credencial_id)

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
	if payload.new_password != payload.confirm_new_password:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="confirm_new_password no coincide con new_password",
		)

	ok = resetear_password(db, payload.token, payload.new_password)
	if not ok:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalido o expirado")

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
	credencial = get_credencial_by_id(db, credencial_id)

	if not credencial:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credencial no encontrada")

	return {
		"credencial_id": str(credencial.credencial_id),
		"correo": credencial.correo,
		"rol": credencial.rol,
		"activo": credencial.activo,
		"tiene_2fa": credencial.tiene_2fa,
	}
