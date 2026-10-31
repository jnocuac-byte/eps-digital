import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt

from app.agents import tools
from app.core.auth import verify_access_token
from app.core.turn_context import TurnContext
from app.core.conversation_state import ConversationState


SECRET = "test-secret"


def _token(**claims):
    payload = {
        "sub": str(uuid4()),
        "usuario_id": str(uuid4()),
        "tipo": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        **claims,
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def test_verify_access_token_accepts_valid_token_and_rejects_invalid_variants(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    usuario_id = uuid4()
    token = _token(usuario_id=str(usuario_id))
    assert verify_access_token(f"Bearer {token}") == usuario_id

    cases = [
        None,
        "Basic token",
        f"Bearer {_token(exp=datetime.now(timezone.utc) - timedelta(seconds=1))}",
        f"Bearer {token[:-1]}x",
        f"Bearer {_token(tipo='refresh')}",
        f"Bearer {_token(usuario_id='not-a-uuid')}",
        f"Bearer {_token(usuario_id='00000000-0000-0000-0000-000000000000')}",
        f"Bearer {_token(usuario_id=None)}",
    ]
    for authorization in cases:
        with pytest.raises(HTTPException) as exc_info:
            verify_access_token(authorization)
        assert exc_info.value.status_code == 401


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        verify_access_token("Bearer token")
    assert exc_info.value.status_code == 503


class _Response:
    status_code = 200

    def json(self):
        return []


class _Client:
    last_request = None

    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def get(self, url, headers=None):
        self.last_request = ("GET", url, headers)
        return _Response()

    def post(self, url, json=None, headers=None):
        self.last_request = ("POST", url, json, headers)
        return _Response()


def test_legacy_user_id_argument_is_ignored_by_citation_tools(monkeypatch):
    verified_id = str(uuid4())
    context = type(
        "Context",
        (),
        {
            "invocation_state": {
                "usuario_id": verified_id,
                "turn_context": TurnContext("conv", verified_id, ConversationState()),
            }
        },
    )()
    client = _Client()
    monkeypatch.setenv("CITAS_SERVICE_URL", "http://citas")
    monkeypatch.setattr(tools.httpx, "Client", lambda **kwargs: client)

    listed = json.loads(
        tools.consultar_citas_usuario.__wrapped__(
            "attacker-id", tool_context=context
        )
    )
    assert listed["ok"] is True
    assert client.last_request[1].endswith(f"/citas/usuario/{verified_id}")

    tools.reagendar_cita.__wrapped__(
        "attacker-id",
        str(uuid4()),
        "2026-11-02",
        "09:00",
        tool_context=context,
    )
    assert client.last_request[3]["X-User-ID"] == verified_id

    tools.cancelar_cita.__wrapped__(
        "attacker-id",
        str(uuid4()),
        tool_context=context,
    )
    assert client.last_request[3]["X-User-ID"] == verified_id


def test_citation_tools_require_verified_identity():
    context = type("Context", (), {"invocation_state": {}})()
    assert "identidad autenticada" in tools.consultar_citas_usuario.__wrapped__(
        "attacker-id", tool_context=context
    )
    assert "identidad autenticada" in tools.reagendar_cita.__wrapped__(
        "attacker-id",
        str(uuid4()),
        "2026-11-02",
        "09:00",
        tool_context=context,
    )
    assert "identidad autenticada" in tools.cancelar_cita.__wrapped__(
        "attacker-id",
        str(uuid4()),
        tool_context=context,
    )
