"""Logica de negocio de autenticacion para el Auth Service."""

from __future__ import annotations

import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, UTC

import bcrypt
import httpx
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Credencial, LogAutenticacion, Registro2FA, TokenRecuperacion
from app.schemas import UserRegister


# 1. Configuracion de bcrypt y JWT
BCRYPT_ROUNDS = 12

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
RECOVERY_TOKEN_EXPIRE_MINUTES = 30
TWO_FA_CODE_EXPIRE_MINUTES = 10
MAX_INTENTOS_FALLIDOS = 5
BLOQUEO_MINUTES = 15
USER_SERVICE_TIMEOUT_SECONDS = 5.0


class DocumentoNoEncontradoError(ValueError):
	"""Error de dominio para documento no encontrado en User Service."""


class UserServiceUnavailableError(ValueError):
	"""Error para caidas, timeout o respuestas invalidas de User Service."""


def _get_jwt_secret_key() -> str:
	"""Obtiene la clave secreta JWT desde variable de entorno."""
	secret = os.getenv("JWT_SECRET_KEY")
	if not secret:
		raise ValueError("JWT_SECRET_KEY no esta configurada en el entorno")
	return secret


def _get_user_service_url() -> str:
	"""Obtiene URL base de User Service desde variable de entorno."""
	base_url = os.getenv("USER_SERVICE_URL")
	if not base_url:
		raise UserServiceUnavailableError("USER_SERVICE_URL no esta configurada")
	return base_url.rstrip("/")


# 2. Funciones de hashing y verificacion
def hash_password(password: str) -> str:
	"""Genera hash bcrypt para una contrasena en texto plano."""
	password_bytes = password.encode("utf-8")
	if len(password_bytes) > 72:
		raise ValueError("La contrasena no puede superar 72 bytes para bcrypt")
	return bcrypt.hashpw(
		password_bytes,
		bcrypt.gensalt(rounds=BCRYPT_ROUNDS),
	).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
	"""Verifica una contrasena contra su hash bcrypt."""
	try:
		return bcrypt.checkpw(
			plain_password.encode("utf-8"),
			password_hash.encode("utf-8"),
		)
	except ValueError:
		return False


def _sha256_hex(value: str) -> str:
	"""Devuelve SHA256 hexadecimal para tokens de uso temporal."""
	return hashlib.sha256(value.encode("utf-8")).hexdigest()


# 3. Funciones de JWT (crear y verificar)
def create_jwt_token(
	credencial_id: uuid.UUID,
	tipo: str,
	expires_delta: timedelta,
) -> str:
	"""Crea un JWT firmado para access o refresh token."""
	now = datetime.now(UTC)
	payload = {
		"sub": str(credencial_id),
		"iat": int(now.timestamp()),
		"exp": int((now + expires_delta).timestamp()),
		"tipo": tipo,
	}
	secret_key = _get_jwt_secret_key()
	return jwt.encode(payload, secret_key, algorithm=JWT_ALGORITHM)


def create_access_token(credencial_id: uuid.UUID) -> str:
	"""Crea access token con expiracion de 30 minutos."""
	return create_jwt_token(
		credencial_id=credencial_id,
		tipo="access",
		expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
	)


def create_refresh_token(credencial_id: uuid.UUID) -> str:
	"""Crea refresh token con expiracion de 7 dias."""
	return create_jwt_token(
		credencial_id=credencial_id,
		tipo="refresh",
		expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
	)


def verify_jwt_token(token: str, expected_tipo: str | None = None) -> dict:
	"""Verifica firma/expiracion JWT y opcionalmente valida su tipo."""
	try:
		payload = jwt.decode(token, _get_jwt_secret_key(), algorithms=[JWT_ALGORITHM])
	except ExpiredSignatureError as exc:
		raise ValueError("Token JWT expirado") from exc
	except JWTError as exc:
		raise ValueError("Token JWT invalido o expirado") from exc

	token_tipo = payload.get("tipo")
	if expected_tipo and token_tipo != expected_tipo:
		raise ValueError("Tipo de token JWT no valido")

	sub = payload.get("sub")
	if not sub:
		raise ValueError("Token JWT sin subject")

	return payload


def refresh_access_token(db: Session, refresh_token: str) -> str:
    """Verifica refresh token y genera nuevo access token."""
    payload = verify_jwt_token(refresh_token, expected_tipo="refresh")
    credencial_id = uuid.UUID(payload["sub"])
    credencial = get_credencial_by_id(db, credencial_id)
    if not credencial or not credencial.activo:
        raise ValueError("Credencial invalida o inactiva")
    return create_access_token(credencial_id)


# 7. Funciones auxiliares
def get_credencial_by_id(db: Session, credencial_id: uuid.UUID) -> Credencial | None:
	"""Obtiene credencial por su identificador."""
	stmt = select(Credencial).where(Credencial.credencial_id == credencial_id)
	return db.execute(stmt).scalars().first()

def get_credencial_by_correo(db: Session, correo: str) -> Credencial | None:
	"""Obtiene credencial por correo (normalizado en minusculas)."""
	stmt = select(Credencial).where(Credencial.correo == correo.lower().strip())
	return db.execute(stmt).scalars().first()


def get_correo_by_documento(
	db: Session,
	tipo_documento: str,
	numero_documento: str,
) -> str:
	"""Consulta User Service por documento y retorna el correo asociado."""
	# La firma conserva db para mantener coherencia con funciones de negocio del servicio.
	_ = db

	params = {
		"tipo_documento": tipo_documento.strip().upper(),
		"numero_documento": numero_documento.strip(),
	}
	url = f"{_get_user_service_url()}/usuarios/buscar"

	try:
		response = httpx.get(url, params=params, timeout=USER_SERVICE_TIMEOUT_SECONDS)
	except httpx.TimeoutException as exc:
		raise UserServiceUnavailableError(
			"User Service no responde (timeout al consultar documento)",
		) from exc
	except httpx.RequestError as exc:
		raise UserServiceUnavailableError(
			"No se pudo conectar con User Service",
		) from exc

	if response.status_code == 404:
		raise DocumentoNoEncontradoError("Documento no encontrado")

	if response.status_code >= 500:
		raise UserServiceUnavailableError("User Service no disponible")

	if response.status_code != 200:
		raise ValueError("No fue posible validar el documento en User Service")

	try:
		payload = response.json()
	except ValueError as exc:
		raise UserServiceUnavailableError("Respuesta invalida de User Service") from exc

	correo = payload.get("correo")
	if not isinstance(correo, str) or not correo.strip():
		raise UserServiceUnavailableError("User Service no retorno un correo valido")

	return correo.lower().strip()


def verificar_bloqueo(credencial: Credencial) -> bool:
	"""Retorna True si la credencial sigue bloqueada a la fecha actual."""
	if credencial.bloqueado_hasta is None:
		return False
	return credencial.bloqueado_hasta > datetime.now(UTC)


# 8. Funciones de auditoria
def log_evento(
	db: Session,
	credencial_id: uuid.UUID,
	evento: str,
	ip: str | None,
	user_agent: str | None,
) -> None:
	"""Registra un evento de autenticacion para auditoria."""
	log = LogAutenticacion(
		credencial_id=credencial_id,
		evento=evento,
		ip_origen=ip,
		agente_usuario=user_agent,
	)
	db.add(log)


# 4. Funciones de recuperacion (crear token, resetear)
def crear_token_recuperacion(db: Session, credencial_id: uuid.UUID) -> str:
	"""Genera token de recuperacion, guarda su hash y devuelve token_hash."""
	raw_token = secrets.token_urlsafe(32)
	token_hash = _sha256_hex(raw_token)

	recovery = TokenRecuperacion(
		credencial_id=credencial_id,
		token_hash=token_hash,
		expira_en=datetime.now(UTC) + timedelta(minutes=RECOVERY_TOKEN_EXPIRE_MINUTES),
		usado=False,
	)
	db.add(recovery)
	db.commit()

	return token_hash


def resetear_password(db: Session, raw_token: str, new_password: str) -> bool:
	"""Resetea contrasena usando token valido, no usado y no expirado."""
	now = datetime.now(UTC)
	token_hash = _sha256_hex(raw_token)

	stmt = (
		select(TokenRecuperacion)
		.where(TokenRecuperacion.token_hash.in_(token_hash))
		.order_by(desc(TokenRecuperacion.creado_en))
	)
	recovery = db.execute(stmt).scalars().first()
	if not recovery:
		return False

	if recovery.usado or recovery.expira_en <= now:
		return False

	credencial = get_credencial_by_id(db, recovery.credencial_id)
	if not credencial:
		return False

	recovery.usado = True
	credencial.password_hash = hash_password(new_password)
	credencial.intentos_fallidos = 0
	credencial.bloqueado_hasta = None

	log_evento(
		db=db,
		credencial_id=credencial.credencial_id,
		evento="password_reset",
		ip=None,
		user_agent=None,
	)

	db.commit()
	return True


# 5. Funciones de 2FA (generar codigo, verificar)
def generar_codigo_2fa(db: Session, credencial_id: uuid.UUID) -> str:
	"""Genera OTP de 6 digitos, guarda hash y devuelve codigo en claro."""
	otp_code = f"{secrets.randbelow(1_000_000):06d}"
	codigo_hash = _sha256_hex(otp_code)

	registro = Registro2FA(
		credencial_id=credencial_id,
		codigo_hash=codigo_hash,
		expira_en=datetime.now(UTC) + timedelta(minutes=TWO_FA_CODE_EXPIRE_MINUTES),
		usado=False,
	)
	db.add(registro)
	db.commit()

	return otp_code


def verificar_codigo_2fa(
	db: Session,
	credencial_id: uuid.UUID,
	codigo: str,
	ip: str | None = None,
	user_agent: str | None = None,
) -> bool:
	"""Verifica OTP 2FA, marca usado y registra el resultado en auditoria."""
	now = datetime.now(UTC)
	stmt = (
		select(Registro2FA)
		.where(
			Registro2FA.credencial_id == credencial_id,
			Registro2FA.usado.is_(False),
		)
		.order_by(desc(Registro2FA.creado_en))
	)
	registro = db.execute(stmt).scalars().first()

	if not registro:
		log_evento(db, credencial_id, "2fa_verificacion_fallida", ip, user_agent)
		db.commit()
		return False

	if registro.expira_en <= now:
		log_evento(db, credencial_id, "2fa_codigo_expirado", ip, user_agent)
		db.commit()
		return False

	if registro.codigo_hash != _sha256_hex(codigo):
		log_evento(db, credencial_id, "2fa_verificacion_fallida", ip, user_agent)
		db.commit()
		return False

	registro.usado = True
	log_evento(db, credencial_id, "2fa_verificacion_exitosa", ip, user_agent)
	db.commit()
	return True


def configurar_2fa(db: Session, credencial_id: uuid.UUID, habilitar: bool) -> bool:
	"""Activa o desactiva 2FA en la credencial indicada."""
	credencial = get_credencial_by_id(db, credencial_id)
	if not credencial:
		return False

	credencial.tiene_2fa = habilitar
	evento = "2fa_activada" if habilitar else "2fa_desactivada"
	log_evento(db, credencial_id, evento, ip=None, user_agent=None)
	db.commit()
	return True


# 6. Funciones de login (autenticar, manejar intentos)
def autenticar_usuario(
	db: Session,
	correo: str,
	password: str,
	ip: str | None = None,
	user_agent: str | None = None,
) -> tuple[uuid.UUID, bool]:
	"""Autentica por correo/password y aplica reglas de bloqueo por intentos."""
	credencial = get_credencial_by_correo(db, correo)
	if not credencial:
		raise ValueError("Credenciales invalidas")

	if verificar_bloqueo(credencial):
		log_evento(db, credencial.credencial_id, "login_rechazado_bloqueo", ip, user_agent)
		db.commit()
		raise ValueError("Cuenta bloqueada temporalmente")

	if not verify_password(password, credencial.password_hash):
		credencial.intentos_fallidos += 1
		if credencial.intentos_fallidos > MAX_INTENTOS_FALLIDOS:
			credencial.bloqueado_hasta = datetime.now(UTC) + timedelta(minutes=BLOQUEO_MINUTES)
			log_evento(db, credencial.credencial_id, "login_fallido_bloqueo", ip, user_agent)
		else:
			log_evento(db, credencial.credencial_id, "login_fallido", ip, user_agent)
		db.commit()
		raise ValueError("Credenciales invalidas")

	credencial.intentos_fallidos = 0
	credencial.bloqueado_hasta = None
	log_evento(db, credencial.credencial_id, "login_exitoso", ip, user_agent)
	db.commit()

	return credencial.credencial_id, credencial.tiene_2fa


def generar_tokens_para_credencial(credencial_id: uuid.UUID) -> tuple[str, str]:
	"""Genera par de tokens (access, refresh) para una credencial."""
	access_token = create_access_token(credencial_id)
	refresh_token = create_refresh_token(credencial_id)
	return access_token, refresh_token


# 7. Funciones de registro
def registrar_usuario(
	db: Session,
	registro: UserRegister,
	usuario_id: uuid.UUID | None = None,
	rol: str = "usuario",
	ip: str | None = None,
	user_agent: str | None = None,
) -> Credencial:
	"""Registra credencial de usuario validando unicidad de correo."""
	correo_normalizado = registro.correo.lower().strip()
	existente = get_credencial_by_correo(db, correo_normalizado)
	if existente:
		raise ValueError("El correo ya esta registrado")

	credencial = Credencial(
		credencial_id=uuid.uuid4(),
		usuario_id= usuario_id if usuario_id is not None else uuid.uuid4(), 
		correo=correo_normalizado,
		password_hash=hash_password(registro.password),
		rol=rol,
		activo=True,
		intentos_fallidos=0,
		tiene_2fa=False,
	)

	db.add(credencial)
	db.flush()

	log_evento(
		db=db,
		credencial_id=credencial.credencial_id,
		evento="registro_exitoso",
		ip=ip,
		user_agent=user_agent,
	)

	db.commit()
	db.refresh(credencial)
	return credencial