import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from jose import jwt

from app.agents import tools
from app.core.auth import verify_access_token
from app.core.turn_context import TurnContext
from app.core.conversation_state import ConversationState
from app import main


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
        # Tamper determinista: cambia un byte INTERMEDIO de la firma (el ultimo
        # caracter base64url solo usa 4 bits; cambiarlo podia decodificar igual).
        f"Bearer {token[:-10]}{'A' if token[-10] != 'A' else 'B'}{token[-9:]}",
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


def test_chat_enforces_token_ownership_and_recreates_missing_conversations(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", SECRET)
    conversations = {}
    created = []

    def create_conversation(_db, usuario_id):
        conversation = SimpleNamespace(
            conversacion_id=uuid4(),
            usuario_id=usuario_id,
            estado="activa",
        )
        conversations[conversation.conversacion_id] = conversation
        created.append(conversation)
        return conversation

    def get_conversation(_db, conversation_id):
        return conversations.get(conversation_id)

    class FakeOrchestrator:
        async def process(self, **_kwargs):
            return "respuesta", ConversationState()

    @asynccontextmanager
    async def no_lifespan(_app):
        yield

    monkeypatch.setattr(main.app.router, "lifespan_context", no_lifespan)
    monkeypatch.setattr(main, "crear_conversacion", create_conversation)
    monkeypatch.setattr(main, "get_conversacion", get_conversation)
    monkeypatch.setattr(main, "crear_mensaje", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main, "get_mensajes_by_conversacion", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(main, "get_clasificacion_by_conversacion", lambda *_args: None)
    monkeypatch.setattr(main.app.state, "orchestrator", FakeOrchestrator(), raising=False)
    main.app.dependency_overrides[main.get_db] = lambda: iter([object()])

    user_a = uuid4()
    user_b = uuid4()
    token_a = _token(usuario_id=str(user_a))
    token_b = _token(usuario_id=str(user_b))
    headers_a = {
        "Authorization": f"Bearer {token_a}",
        "X-User-ID": str(user_b),
    }

    try:
        with TestClient(main.app) as client:
            missing_auth = client.post("/chat", json={"mensaje": "hola"})
            assert missing_auth.status_code == 401

            first = client.post(
                "/chat",
                headers=headers_a,
                json={
                    "mensaje": "hola",
                    "usuario_id": str(user_b),
                },
            )
            assert first.status_code == 200
            first_id = UUID(first.json()["conversacion_id"])
            assert created[-1].usuario_id == user_a

            second = client.post(
                "/chat",
                headers={"Authorization": f"Bearer {token_b}"},
                json={"mensaje": "hola", "conversacion_id": str(first_id)},
            )
            assert second.status_code == 200
            assert second.json()["conversacion_id"] != str(first_id)
            assert created[-1].usuario_id == user_b

            missing = client.post(
                "/chat",
                headers={"Authorization": f"Bearer {token_b}"},
                json={
                    "mensaje": "hola",
                    "conversacion_id": str(uuid4()),
                },
            )
            assert missing.status_code == 200
            assert missing.json()["conversacion_id"] != str(first_id)
    finally:
        main.app.dependency_overrides.clear()
