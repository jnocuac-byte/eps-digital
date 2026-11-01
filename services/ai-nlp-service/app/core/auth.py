from __future__ import annotations

import os
from uuid import UUID

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from .logger import log_event

JWT_ALGORITHM = "HS256"


def verify_access_token(authorization: str | None) -> UUID:
    """Valida el Bearer access token y devuelve el usuario_id autenticado."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación para usar el asistente.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
        )

    secret = os.getenv("JWT_SECRET_KEY", "").strip()
    if not secret:
        log_event("AUTH", "JWT", "error", "JWT_SECRET_KEY no configurada en ai-nlp-service")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La autenticación no está disponible temporalmente.",
        )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[JWT_ALGORITHM],
            options={"require_exp": True, "require_sub": True},
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación expirado.",
        ) from exc
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
        ) from exc

    if payload.get("tipo") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no es válido para esta operación.",
        )

    try:
        UUID(str(payload["sub"]))
        usuario_id = UUID(str(payload["usuario_id"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identidad de usuario válida.",
        ) from exc

    if usuario_id.int == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identidad de usuario válida.",
        )

    return usuario_id
