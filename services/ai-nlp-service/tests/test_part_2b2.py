import asyncio
import json
from datetime import datetime, timedelta
from uuid import uuid4

from app.agents import tools
from app.core.conversation_state import BookingDraft, ConversationState
from app.core.orchestrator import (
    Orchestrator,
    ZONA_BOGOTA,
    _is_affirmative,
    _success_message,
    render_booking_summary,
)
from app.core.turn_context import TurnContext


class _FakeHooks:
    def add_callback(self, *_args, **_kwargs):
        return None


class _FakeAgent:
    def __init__(self, response="respuesta", on_call=None):
        self.messages = []
        self._provider_used = "fake"
        self.hooks = _FakeHooks()
        self.response = response
        self.on_call = on_call
        self.calls = 0

    def __call__(self, _message, **_kwargs):
        self.calls += 1
        if self.on_call:
            self.on_call(_kwargs.get("invocation_state"))
        return self.response


def _draft(usuario_id: str) -> BookingDraft:
    return BookingDraft(
        usuario_id=usuario_id,
        especialidad_id=str(uuid4()),
        especialidad_nombre="Medicina General",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gómez",
        sede_id=str(uuid4()),
        sede_nombre="Sede Central",
        sede_direccion="Calle 1",
        tipo_servicio="medicina_general",
        fecha="2026-11-02",
        hora_inicio="07:00",
        hora_fin="07:20",
        descripcion_sintomas="Fiebre",
    )


def _ready_state(orchestrator, conversation_id, usuario_id):
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = str(uuid4())
    state.specialty_name = "Medicina General"
    state.pending_action = "agendar"
    state.booking_draft = _draft(usuario_id)
    state.message_count = 1
    state.draft_shown_message_count = 1
    state.draft_expires_at = (
        datetime.now(ZONA_BOGOTA) + timedelta(minutes=5)
    ).isoformat()
    return state


def test_confirmation_executes_one_post_without_llm(monkeypatch):
    usuario_id = str(uuid4())
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "confirmation-once"
    _ready_state(orchestrator, conversation_id, usuario_id)
    calls = []

    def fake_create(draft):
        calls.append(draft)
        return {"ok": True, "cita_id": str(uuid4())}

    monkeypatch.setattr(tools, "crear_cita_desde_draft", fake_create)

    response, state = asyncio.run(
        orchestrator.process(
            conversation_id,
            "SI CONFIRMO",
            [],
            usuario_id=usuario_id,
        )
    )

    assert len(calls) == 1
    assert agent.calls == 0
    assert "cita_id" not in response
    assert state.pending_action is None
    assert state.booking_draft is None


def test_confirmation_phrases_and_ambiguous_messages(monkeypatch):
    for phrase in ("SI CONFIRMO", "si por favor agendala", "confirmo"):
        usuario_id = str(uuid4())
        orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
        conversation_id = f"phrase-{phrase[:4]}"
        _ready_state(orchestrator, conversation_id, usuario_id)
        calls = []
        monkeypatch.setattr(
            tools,
            "crear_cita_desde_draft",
            lambda draft, calls=calls: calls.append(draft) or {"ok": True, "cita_id": "id"},
        )
        asyncio.run(orchestrator.process(conversation_id, phrase, [], usuario_id=usuario_id))
        assert len(calls) == 1

    usuario_id = str(uuid4())
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "ambiguous"
    _ready_state(orchestrator, conversation_id, usuario_id)
    response, state = asyncio.run(
        orchestrator.process(
            conversation_id,
            "sí pero mejor a las 8",
            [],
            usuario_id=usuario_id,
        )
    )
    assert response.startswith("respuesta")
    assert "RESUMEN OFICIAL DE LA CITA" in response
    assert agent.calls == 1
    assert state.booking_draft is not None


def test_expired_or_stale_draft_does_not_execute(monkeypatch):
    usuario_id = str(uuid4())
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    state = _ready_state(orchestrator, "expired", usuario_id)
    state.draft_expires_at = (
        datetime.now(ZONA_BOGOTA) - timedelta(seconds=1)
    ).isoformat()
    response, _ = asyncio.run(
        orchestrator.process("expired", "SI CONFIRMO", [], usuario_id=usuario_id)
    )
    assert response.startswith("respuesta")
    assert "RESUMEN OFICIAL DE LA CITA" not in response
    assert agent.calls == 1

    state = _ready_state(orchestrator, "stale", usuario_id)
    state.draft_shown_message_count = 0
    response, _ = asyncio.run(
        orchestrator.process("stale", "SI CONFIRMO", [], usuario_id=usuario_id)
    )
    assert response.startswith("respuesta")
    assert "RESUMEN OFICIAL DE LA CITA" in response
    assert agent.calls == 2


def test_draft_rehydration_and_repeated_confirmation(monkeypatch):
    usuario_id = str(uuid4())
    draft = _draft(usuario_id)
    state = ConversationState(
        pending_action="agendar",
        booking_draft=draft,
        draft_shown_message_count=3,
        draft_expires_at=(datetime.now(ZONA_BOGOTA) + timedelta(minutes=5)).isoformat(),
    )
    restored = ConversationState.from_dict(state.to_dict())
    assert restored.booking_draft == draft

    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "repeat-confirmation"
    loaded = orchestrator.get_state(conversation_id)
    loaded.last_booking_id = "confirmed"
    loaded.last_booking_summary = "Tu cita quedó agendada."
    loaded.message_count = 1
    response, _ = asyncio.run(
        orchestrator.process(conversation_id, "SI CONFIRMO", [], usuario_id=usuario_id)
    )
    assert response == "Tu cita quedó agendada."


def test_create_from_draft_uses_slot_end(monkeypatch):
    draft = _draft(str(uuid4()))
    captured = {}

    class _Response:
        status_code = 201

        def json(self):
            return {"cita_id": str(uuid4())}

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, _url, **kwargs):
            captured.update(kwargs)
            return _Response()

    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")
    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())

    result = tools.crear_cita_desde_draft(draft)

    assert result["ok"] is True
    assert captured["json"]["hora_inicio"] == "07:00"
    assert captured["json"]["hora_fin"] == "07:20"


def test_proponer_cita_uses_single_site_and_creates_draft(monkeypatch):
    usuario_id = str(uuid4())
    state = ConversationState(
        specialty_id=str(uuid4()),
        specialty_name="Medicina General",
        symptoms_summary="Fiebre",
    )
    context = TurnContext("proposal", usuario_id, state)
    slot = {
        "medico_id": str(uuid4()),
        "sede_id": str(uuid4()),
        "especialidad_id": state.specialty_id,
        "hora_inicio": "07:00",
        "hora_fin": "07:20",
    }

    class _Response:
        status_code = 200

        def json(self):
            return [slot]

    class _Client:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def get(self, *_args, **_kwargs):
            return _Response()

    def cached(endpoint):
        if endpoint == "/sedes":
            return {"ok": True, "data": [{"sede_id": slot["sede_id"], "nombre": "Central", "direccion": "Calle 1"}]}
        return {"ok": True, "data": {"nombres": "Ana", "apellidos": "Gómez"}}

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")
    monkeypatch.setattr(tools, "_consultar_catalog_service_cached", cached)

    result = json.loads(
        tools.proponer_cita(
            "2026-11-02",
            "07:00",
            sede="central",
            tool_context=type("Context", (), {"invocation_state": {"state": state, "usuario_id": usuario_id, "turn_context": context}})(),
        )
    )

    assert result["ok"] is True
    assert state.booking_draft.sede_nombre == "Central"
    assert state.booking_draft.hora_fin == "07:20"


def test_failed_post_preserves_draft_and_timeout_recovers_existing_cita(monkeypatch):
    usuario_id = str(uuid4())
    draft = _draft(usuario_id)
    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")

    class FailedResponse:
        status_code = 409

    class FailedClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, *_args, **_kwargs):
            return FailedResponse()

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: FailedClient())
    assert tools.crear_cita_desde_draft(draft)["ok"] is False

    class TimeoutClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def post(self, *_args, **_kwargs):
            raise tools.httpx.TimeoutException("lost response")

        def get(self, *_args, **_kwargs):
            class Response:
                status_code = 200

                def json(self):
                    return [{
                        "cita_id": "existing",
                        "estado": "programada",
                        "medico_id": draft.medico_id,
                        "fecha_cita": draft.fecha,
                        "hora_inicio": draft.hora_inicio,
                    }]

            return Response()

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: TimeoutClient())
    result = tools.crear_cita_desde_draft(draft)
    assert result == {"ok": True, "cita_id": "existing", "recovered": True}


def test_explicit_authorization_executes_after_unique_proposal(monkeypatch):
    usuario_id = str(uuid4())
    agent_calls = []
    agent = _FakeAgent(on_call=agent_calls.append)
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "same-turn-auth"
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = str(uuid4())
    state.specialty_name = "Medicina General"

    draft = _draft(usuario_id)

    def fake_agent_call(invocation_state):
        invocation_state["turn_context"].set_draft(draft)

    agent.on_call = fake_agent_call
    calls = []
    monkeypatch.setattr(
        tools,
        "crear_cita_desde_draft",
        lambda value: calls.append(value) or {"ok": True, "cita_id": "created"},
    )
    response, _ = asyncio.run(
        orchestrator.process(
            conversation_id,
            "2026-11-02 a las 07:00, decide tú y agéndala",
            [],
            usuario_id=usuario_id,
        )
    )
    assert response.startswith("Tu cita")
    assert len(calls) == 1


def test_service_type_and_text_normalization():
    assert tools._normalizar_texto("Consulta Medicina General") == "consulta medicina general"
    assert tools._tipo_servicio_desde_especialidad("Consulta Medicina General") == "medicina_general"
    assert tools._tipo_servicio_desde_especialidad("Urgencias") == "urgencias"
    assert tools._tipo_servicio_desde_especialidad("Laboratorio clínico") == "laboratorio"
    assert tools._tipo_servicio_desde_especialidad("Cardiología") == "especialista"


def test_affirmative_messages_are_word_based():
    accepted = ("Sí", "sí por favor", "Confirmo", "sí, agéndala", "dale")
    rejected = ("sí pero a las 8", "no sé", "sí, ¿y la dirección?", "no")
    assert all(_is_affirmative(message) for message in accepted)
    assert not any(_is_affirmative(message) for message in rejected)


def test_failed_booking_refreshes_draft_for_retry(monkeypatch):
    usuario_id = str(uuid4())
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "retry-after-failure"
    state = _ready_state(orchestrator, conversation_id, usuario_id)
    results = iter(
        [
            {"ok": False, "error": "conflict"},
            {"ok": True, "cita_id": "created"},
        ]
    )
    calls = []
    monkeypatch.setattr(
        tools,
        "crear_cita_desde_draft",
        lambda draft: calls.append(draft) or next(results),
    )

    first, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id)
    )
    assert "confirma de nuevo" in first
    assert state.draft_shown_message_count == state.message_count
    second, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id)
    )
    assert second.startswith("Tu cita")
    assert len(calls) == 2
    assert state.execution_started_at is None


def test_new_draft_clears_previous_success_and_allows_second_booking(monkeypatch):
    usuario_id = str(uuid4())
    state_holder = {"calls": 0}
    draft_one = _draft(usuario_id)
    draft_two = _draft(usuario_id)
    draft_two.fecha = "2026-11-03"
    draft_two.hora_inicio = "08:00"
    draft_two.hora_fin = "08:20"

    def on_call(invocation_state):
        draft = draft_one if state_holder["calls"] == 0 else draft_two
        state_holder["calls"] += 1
        invocation_state["turn_context"].set_draft(draft)

    agent = _FakeAgent(on_call=on_call)
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "two-bookings"
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = str(uuid4())
    state.specialty_name = "Medicina General"
    calls = []
    monkeypatch.setattr(
        tools,
        "crear_cita_desde_draft",
        lambda draft: calls.append(draft) or {"ok": True, "cita_id": str(len(calls))},
    )

    asyncio.run(orchestrator.process(conversation_id, "2026-11-02 a las 07:00", [], usuario_id=usuario_id))
    asyncio.run(orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id))
    assert state.last_booking_id == "1"

    asyncio.run(orchestrator.process(conversation_id, "2026-11-03 a las 08:00", [], usuario_id=usuario_id))
    assert state.last_booking_id is None
    asyncio.run(orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id))
    assert len(calls) == 2
    assert calls[1].fecha == "2026-11-03"


def test_non_affirmative_message_clears_old_idempotency_window(monkeypatch):
    usuario_id = str(uuid4())
    agent = _FakeAgent(response="Respuesta del agente")
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "idempotency-window"
    _ready_state(orchestrator, conversation_id, usuario_id)
    calls = []
    monkeypatch.setattr(
        tools,
        "crear_cita_desde_draft",
        lambda draft: calls.append(draft) or {"ok": True, "cita_id": "created"},
    )

    success, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id)
    )
    repeated, _ = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id)
    )
    assert repeated == success

    response, state = asyncio.run(
        orchestrator.process(
            conversation_id,
            "¿qué otras citas tengo?",
            [],
            usuario_id=usuario_id,
        )
    )
    assert response == "Respuesta del agente"
    assert state.last_booking_id is None
    assert state.last_booking_summary is None

    response, _ = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=usuario_id)
    )
    assert response == "Respuesta del agente"
    assert len(calls) == 1


def test_success_message_uses_readable_spanish_date():
    message = _success_message(_draft(str(uuid4())))
    assert "lunes 2 de noviembre de 2026" in message
    assert "07:00 a 07:20" in message
