from datetime import timedelta
from uuid import uuid4

import pytest
from jose import jwt

from app import auth


def test_access_and_refresh_tokens_include_usuario_id(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    credencial_id = uuid4()
    usuario_id = uuid4()

    access = auth.create_access_token(credencial_id, usuario_id)
    refresh = auth.create_refresh_token(credencial_id, usuario_id)

    access_payload = jwt.decode(access, "test-secret", algorithms=["HS256"])
    refresh_payload = jwt.decode(refresh, "test-secret", algorithms=["HS256"])

    assert access_payload["sub"] == str(credencial_id)
    assert access_payload["usuario_id"] == str(usuario_id)
    assert access_payload["tipo"] == "access"
    assert refresh_payload["usuario_id"] == str(usuario_id)
    assert refresh_payload["tipo"] == "refresh"


def test_token_validation_still_enforces_type_and_expiration(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
    credencial_id = uuid4()
    usuario_id = uuid4()

    access = auth.create_access_token(credencial_id, usuario_id)
    assert auth.verify_jwt_token(access, expected_tipo="access")["usuario_id"] == str(usuario_id)

    expired = auth.create_jwt_token(
        credencial_id,
        usuario_id,
        "access",
        timedelta(seconds=-1),
    )
    with pytest.raises(ValueError, match="expirado"):
        auth.verify_jwt_token(expired, expected_tipo="access")

    with pytest.raises(ValueError, match="Tipo"):
        auth.verify_jwt_token(
            auth.create_refresh_token(credencial_id, usuario_id),
            expected_tipo="access",
        )
