"""PR4 pasos 6-7: orquestador — renders oficiales y ejecucion determinista.

Con httpx mockeado y agente falso (sin servicios reales y sin LLM):
- renders: RESUMEN OFICIAL con CANCELAR/REAGENDAR, fecha legible en espanol,
  original y nueva en reagendar, cierra con "¿Confirmas? Responde sí o no.",
  sin UUID.
- mensajes de exito por codigo (cancelada, reagendada, ya estaba cancelada),
  sin UUID.
- _append_booking_summary generalizado por pending_action (sin duplicar).
- dispatch _handle_pending_action: (a) 0 llamadas al proponer y 1 tras "si";
  (b) "no" limpia y el "si" siguiente no ejecuta; (c) doble "si" = 1 sola
  llamada; (d) "si pero mejor el martes" no ejecuta; (e) "de una vez" no
  ejecuta y re-muestra; (f) cita cambiada/cancelada por otro canal;
  (g) cupo ocupado; (h) fallo transitorio con reintento; (i) rehidratacion;
  (j) draft de agendar reemplazado; (k) cita_id vacio o usuario distinto
  nunca ejecutan y limpian; (l) regresion de agendar (test_part_2b2 intacto).
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from app.agents import tools
from app.core.conversation_state import (
    BookingDraft,
    CancelDraft,
    ConversationState,
    RescheduleDraft,
)
from app.core.orchestrator import (
    Orchestrator,
    ZONA_BOGOTA,
    render_cancel_summary,
    render_reschedule_summary,
)
from app.core.turn_context import TurnContext

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

USUARIO = str(uuid4())
CITA_ID = str(uuid4())


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


def _booking_draft(usuario_id=USUARIO) -> BookingDraft:
    return BookingDraft(
        usuario_id=usuario_id,
        especialidad_id=str(uuid4()),
        especialidad_nombre="Medicina General",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gómez",
        sede_id=str(uuid4()),
        sede_nombre="Sede Norte",
        sede_direccion="Calle 1",
        tipo_servicio="medicina_general",
        fecha="2026-11-02",
        hora_inicio="07:00",
        hora_fin="07:20",
        descripcion_sintomas="Fiebre",
    )


def _cancel_draft(cita_id=CITA_ID, usuario_id=USUARIO) -> CancelDraft:
    return CancelDraft(
        cita_id=cita_id,
        usuario_id=usuario_id,
        fecha="2026-11-02",
        hora_inicio="10:00",
        hora_fin="10:30",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gómez",
        sede_id=str(uuid4()),
        sede_nombre="Sede Norte",
        especialidad_nombre="Medicina General",
        motivo="cambio de planes",
    )


def _reschedule_draft(cita_id=CITA_ID, usuario_id=USUARIO) -> RescheduleDraft:
    return RescheduleDraft(
        cita_id=cita_id,
        usuario_id=usuario_id,
        fecha_original="2026-11-02",
        hora_inicio_original="10:00",
        hora_fin_original="10:30",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gómez",
        sede_id=str(uuid4()),
        sede_nombre="Sede Norte",
        especialidad_nombre="Medicina General",
        nueva_fecha="2026-11-05",
        nueva_hora_inicio="08:00",
        nueva_hora_fin="08:30",
    )


def _cita_activa(cita_id=CITA_ID, fecha="2026-11-02", hora="10:00"):
    return {
        "cita_id": cita_id,
        "estado": "programada",
        "fecha_cita": fecha,
        "hora_inicio": hora,
        "hora_fin": "10:30",
    }


def _state_listo(orchestrator, conversation_id, action, draft):
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = str(uuid4())
    state.specialty_name = "Medicina General"
    state.pending_action = action
    if action == "cancelar":
        state.cancel_draft = draft
    elif action == "reagendar":
        state.reschedule_draft = draft
    else:
        state.booking_draft = draft
    state.pending_confirmation = True
    state.message_count = 1
    state.draft_shown_message_count = 1
    state.draft_expires_at = (
        datetime.now(ZONA_BOGOTA) + timedelta(minutes=5)
    ).isoformat()
    return state


def _mockear_citas_activas(monkeypatch, citas):
    """Mockea la re-verificacion del orquestador; devuelve las llamadas."""
    llamadas = []

    def fake(usuario_id):
        llamadas.append(usuario_id)
        return {"ok": True, "citas": citas}

    monkeypatch.setattr(tools, "_obtener_citas_activas", fake)
    return llamadas


def _mockear_ejecutor(monkeypatch, nombre, resultados):
    """Mockea un ejecutor con una lista/iterador de resultados por llamada."""
    llamadas = []
    iterator = iter(resultados)

    def fake(draft, usuario_id):
        llamadas.append({"draft": draft, "usuario_id": usuario_id})
        return next(iterator)

    monkeypatch.setattr(tools, nombre, fake)
    return llamadas


# ---------------------------------------------------------------------------
# Paso 6: renders oficiales y mensajes de exito por codigo
# ---------------------------------------------------------------------------


def test_render_cancel_summary_oficial_sin_uuid():
    draft = _cancel_draft()
    texto = render_cancel_summary(draft)

    assert texto.startswith("RESUMEN OFICIAL DE LA CANCELACIÓN")
    assert "CANCELAR" in texto
    assert "lunes 02/11/2026" in texto
    assert "10:00 - 10:30" in texto
    assert "Ana Gómez" in texto
    assert "Sede Norte" in texto
    assert "Medicina General" in texto
    assert "cambio de planes" in texto
    assert texto.endswith("¿Confirmas? Responde sí o no.")
    assert not UUID_REGEX.search(texto)


def test_render_reschedule_summary_oficial_sin_uuid():
    draft = _reschedule_draft()
    texto = render_reschedule_summary(draft)

    assert texto.startswith("RESUMEN OFICIAL DEL REAGENDAMIENTO")
    assert "REAGENDAR" in texto
    # Original y nueva, con fecha legible en espanol.
    assert "Cita actual: lunes 02/11/2026, de 10:00 a 10:30" in texto
    assert "Nueva fecha: jueves 05/11/2026" in texto
    assert "Nueva hora: 08:00 - 08:30" in texto
    assert "Ana Gómez" in texto
    assert "Sede Norte" in texto
    assert texto.endswith("¿Confirmas? Responde sí o no.")
    assert not UUID_REGEX.search(texto)


def test_append_summary_generalizado_por_pending_action():
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    state = orchestrator.get_state("append-dispatch")
    state.message_count = 3
    state.pending_action = "cancelar"
    state.cancel_draft = _cancel_draft()

    respuesta = orchestrator._append_booking_summary(
        state, "Claro, preparo la cancelación."
    )

    assert "Claro, preparo la cancelación." in respuesta
    assert "RESUMEN OFICIAL DE LA CANCELACIÓN" in respuesta
    assert state.draft_shown_message_count == 3
    assert state.draft_expires_at is not None

    # Reemplaza (no duplica) si la respuesta ya trae un resumen previo.
    repetida = orchestrator._append_booking_summary(state, respuesta)
    assert repetida.count("RESUMEN OFICIAL DE LA CANCELACIÓN") == 1


def test_mensajes_de_exito_cancelar_y_reagendar_sin_uuid():
    cancel = _cancel_draft()
    ya_cancelada = _cancel_draft()
    reagendar = _reschedule_draft()

    from app.core.orchestrator import (
        _success_cancel_message,
        _success_reschedule_message,
        _success_ya_cancelada_message,
    )

    cancelado = _success_cancel_message(cancel)
    repetida = _success_ya_cancelada_message(ya_cancelada)
    reprogramada = _success_reschedule_message(reagendar)

    assert "fue cancelada" in cancelado
    assert "lunes 2 de noviembre de 2026" in cancelado
    assert "ya estaba cancelada" in repetida
    assert "no hacía falta" in repetida
    assert "fue reprogramada" in reprogramada
    assert "jueves 5 de noviembre de 2026" in reprogramada
    assert "08:00 a 08:30" in reprogramada
    for mensaje in (cancelado, repetida, reprogramada):
        assert not UUID_REGEX.search(mensaje)


# ---------------------------------------------------------------------------
# Paso 7: (a) proponer no ejecuta; el "si" ejecuta exactamente UNA vez
# ---------------------------------------------------------------------------


def test_cancelar_propuesta_cero_llamadas_y_si_ejecuta_una_vez(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    verificaciones = _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent(
        on_call=lambda invocation_state: invocation_state["turn_context"].set_draft(
            _cancel_draft(), "cancelar"
        )
    )
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "cancelar-propuesta"
    preparado = orchestrator.get_state(conversation_id)
    preparado.active_agent = "scheduling"
    preparado.specialty_id = str(uuid4())
    preparado.specialty_name = "Medicina General"

    # Turno de propuesta: resumen oficial, CERO llamadas de cancelacion.
    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "cancela mi cita del lunes", [], usuario_id=USUARIO
        )
    )
    assert "RESUMEN OFICIAL DE LA CANCELACIÓN" in respuesta
    assert "¿Confirmas? Responde sí o no." in respuesta
    assert cancel_calls == []
    assert state.pending_action == "cancelar"

    # Turno "si": exactamente UNA llamada de cancelacion con el cita_id del
    # draft y el usuario VERIFICADO; sin UUID en la respuesta.
    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert cancel_calls[0]["draft"].cita_id == CITA_ID
    assert cancel_calls[0]["usuario_id"] == USUARIO
    assert verificaciones == [USUARIO]
    assert agent.calls == 1  # el "si" no paso por el agente
    assert "fue cancelada" in respuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.cancel_draft is None
    assert state.pending_action is None
    assert state.last_booking_summary == respuesta


def test_reagendar_propuesta_y_si_ejecuta_una_vez(monkeypatch):
    reagendar_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_reagendamiento_desde_draft",
        [{"ok": True}],
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent(
        on_call=lambda invocation_state: invocation_state["turn_context"].set_draft(
            _reschedule_draft(), "reagendar"
        )
    )
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "reagendar-propuesta"
    preparado = orchestrator.get_state(conversation_id)
    preparado.active_agent = "scheduling"
    preparado.specialty_id = str(uuid4())
    preparado.specialty_name = "Medicina General"

    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "reagendar mi cita del lunes", [], usuario_id=USUARIO
        )
    )
    assert "RESUMEN OFICIAL DEL REAGENDAMIENTO" in respuesta
    assert reagendar_calls == []

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(reagendar_calls) == 1
    assert reagendar_calls[0]["draft"].cita_id == CITA_ID
    assert reagendar_calls[0]["usuario_id"] == USUARIO
    assert agent.calls == 1
    assert "fue reprogramada" in respuesta
    assert "jueves 5 de noviembre de 2026" in respuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.reschedule_draft is None
    assert state.pending_action is None


# ---------------------------------------------------------------------------
# (b) "no" limpia el draft; el "si" siguiente NO ejecuta
# ---------------------------------------------------------------------------


def test_no_limpia_draft_y_el_si_siguiente_no_ejecuta(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "no-luego-si"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "no", [], usuario_id=USUARIO)
    )
    assert "no cancelaré" in respuesta
    assert state.cancel_draft is None
    assert state.pending_action is None
    assert cancel_calls == []

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert cancel_calls == []  # sin draft no hay nada que ejecutar
    assert agent.calls == 1


# ---------------------------------------------------------------------------
# (c) Doble "si": una sola llamada, mensaje de exito repetido
# ---------------------------------------------------------------------------


def test_doble_si_una_sola_llamada(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "doble-si"
    _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    primera, _ = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    segunda, _ = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert segunda == primera
    assert "fue cancelada" in segunda


def test_ya_cancelada_es_exito_idempotente(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_cancelacion_desde_draft",
        [{"ok": True, "ya_cancelada": True}],
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "ya-cancelada"
    _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert "ya estaba cancelada" in respuesta
    assert "no hacía falta" in respuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.cancel_draft is None


# ---------------------------------------------------------------------------
# (d) "si pero mejor el martes": NO ejecuta; pasa al agente con draft intacto
# ---------------------------------------------------------------------------


def test_si_pero_mejor_el_martes_no_ejecuta(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "si-ambiguo"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "sí pero mejor el martes", [], usuario_id=USUARIO
        )
    )
    assert cancel_calls == []
    assert agent.calls == 1
    assert respuesta.startswith("respuesta")
    assert "RESUMEN OFICIAL DE LA CANCELACIÓN" in respuesta
    assert state.cancel_draft is not None
    assert state.pending_action == "cancelar"


# ---------------------------------------------------------------------------
# (e) "de una vez" / "no esperes confirmacion": NO ejecuta, re-muestra
# ---------------------------------------------------------------------------


def test_cancelar_de_una_vez_no_ejecuta_y_remuestra_resumen(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "cancelar-apurado"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "cancélala de una vez", [], usuario_id=USUARIO
        )
    )
    assert cancel_calls == []
    assert agent.calls == 0
    assert "RESUMEN OFICIAL DE LA CANCELACIÓN" in respuesta
    assert respuesta.endswith("¿Confirmas? Responde sí o no.")
    assert state.cancel_draft is not None
    # La ventana se refresco: el "si" del turno siguiente SI ejecuta.
    assert state.draft_shown_message_count == state.message_count
    respuesta, _ = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert "fue cancelada" in respuesta


@pytest.mark.parametrize(
    ("action", "message", "executor_name", "draft_factory", "success_text"),
    [
        (
            "cancelar",
            "sí, cancélala de una vez",
            "ejecutar_cancelacion_desde_draft",
            _cancel_draft,
            "fue cancelada",
        ),
        (
            "reagendar",
            "sí, reagéndala de una vez",
            "ejecutar_reagendamiento_desde_draft",
            _reschedule_draft,
            "fue reprogramada",
        ),
    ],
)
def test_autorizacion_apurada_con_si_no_ejecuta_hasta_confirmacion_simple(
    monkeypatch, action, message, executor_name, draft_factory, success_text
):
    calls = _mockear_ejecutor(monkeypatch, executor_name, [{"ok": True}])
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = f"{action}-si-apurado"
    _state_listo(orchestrator, conversation_id, action, draft_factory())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, message, [], usuario_id=USUARIO)
    )
    assert calls == []
    assert "¿Confirmas? Responde sí o no." in respuesta
    assert state.pending_action == action

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(calls) == 1
    assert success_text in respuesta
    assert state.pending_action is None


def test_reagendar_de_una_vez_no_ejecuta_y_remuestra_resumen(monkeypatch):
    reagendar_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_reagendamiento_desde_draft",
        [{"ok": True}],
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "reagendar-apurado"
    _state_listo(orchestrator, conversation_id, "reagendar", _reschedule_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "reagéndala de una vez", [], usuario_id=USUARIO
        )
    )
    assert reagendar_calls == []
    assert agent.calls == 0
    assert "RESUMEN OFICIAL DEL REAGENDAMIENTO" in respuesta
    assert "Nueva fecha: jueves 05/11/2026" in respuesta
    assert state.reschedule_draft is not None


def test_pending_action_sin_draft_no_rompe_ni_ejecuta(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "pending-sin-draft"
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = str(uuid4())
    state.specialty_name = "Medicina General"
    state.pending_action = "cancelar"
    state.message_count = 1

    respuesta, final = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert cancel_calls == []
    assert agent.calls == 1
    assert respuesta == "respuesta"
    assert final.pending_action == "cancelar"


# ---------------------------------------------------------------------------
# (f) Cita cambiada o cancelada por otro canal: no ejecuta y pide nueva propuesta
# ---------------------------------------------------------------------------


def test_cancelar_cita_cancelada_por_otro_canal(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    # Ya no figura entre las programadas (la cancelaron desde la web).
    _mockear_citas_activas(monkeypatch, [])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "cancel-por-otro-canal"
    _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert cancel_calls == []
    assert "cambió" in respuesta
    assert "pídeme de nuevo" in respuesta.lower() or "Pídeme de nuevo" in respuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.cancel_draft is None
    assert state.pending_action is None


def test_reagendar_cita_reprogramada_por_otro_canal(monkeypatch):
    reagendar_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_reagendamiento_desde_draft",
        [{"ok": True}],
    )
    # La cita sigue programada pero su fecha/hora ya NO coinciden con el draft.
    _mockear_citas_activas(
        monkeypatch, [_cita_activa(fecha="2026-11-03", hora="09:00")]
    )
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "reagendar-por-otro-canal"
    _state_listo(orchestrator, conversation_id, "reagendar", _reschedule_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert reagendar_calls == []
    assert "cambió" in respuesta
    assert "reagendamiento" in respuesta  # pide nueva propuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.reschedule_draft is None


def test_reagendar_reverifica_hora_con_segundos(monkeypatch):
    reagendar_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_reagendamiento_desde_draft",
        [{"ok": True}],
    )
    _mockear_citas_activas(
        monkeypatch, [_cita_activa(fecha="2026-11-02", hora="10:00:00")]
    )
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "reagendar-hora-segundos"
    _state_listo(orchestrator, conversation_id, "reagendar", _reschedule_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(reagendar_calls) == 1
    assert "fue reprogramada" in respuesta
    assert state.reschedule_draft is None


# ---------------------------------------------------------------------------
# (g) Cupo ocupado al ejecutar el reagendamiento
# ---------------------------------------------------------------------------


def test_reagendar_cupo_ocupado_limpia_y_pide_nueva_propuesta(monkeypatch):
    reagendar_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_reagendamiento_desde_draft",
        [{"ok": False, "cupo_no_disponible": True, "error": "ocupado"}],
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "cupo-ocupado"
    _state_listo(orchestrator, conversation_id, "reagendar", _reschedule_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(reagendar_calls) == 1
    assert "ya no está disponible" in respuesta
    assert "reagendamiento" in respuesta
    assert not UUID_REGEX.search(respuesta)
    assert state.reschedule_draft is None
    assert state.pending_action is None


# ---------------------------------------------------------------------------
# (h) Fallo transitorio: conserva el draft y permite reintentar
# ---------------------------------------------------------------------------


def test_cancelar_fallo_transitorio_conserva_draft_y_reintenta(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch,
        "ejecutar_cancelacion_desde_draft",
        [{"ok": False, "error": "conflicto"}, {"ok": True}],
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "fallo-transitorio"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    primera, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert "confirma de nuevo" in primera
    assert state.cancel_draft is not None
    assert state.pending_action == "cancelar"
    # Ventana refrescada para que el "si" siguiente reintente.
    assert state.draft_shown_message_count == state.message_count

    segunda, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 2
    assert "fue cancelada" in segunda
    assert state.cancel_draft is None


def test_verificacion_fallida_conserva_draft(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    monkeypatch.setattr(
        tools,
        "_obtener_citas_activas",
        lambda _usuario_id: {"ok": False, "error": "La consulta tardo demasiado."},
    )
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "verificacion-falla"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert cancel_calls == []
    assert "No pude verificar tu cita ahora mismo" in respuesta
    assert state.cancel_draft is not None
    assert state.draft_shown_message_count == state.message_count


# ---------------------------------------------------------------------------
# (i) Rehidratacion desde estado persistido (JSON round-trip)
# ---------------------------------------------------------------------------


def test_rehidratacion_desde_estado_persistido(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    conversation_id = "rehidratacion-cancel"

    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())
    restaurado = ConversationState.from_dict(json.loads(json.dumps(state.to_dict())))
    assert restaurado.cancel_draft == state.cancel_draft
    assert restaurado.pending_action == "cancelar"

    nuevo = Orchestrator(_FakeAgent(), _FakeAgent())
    nuevo._states[conversation_id] = restaurado
    respuesta, final = asyncio.run(
        nuevo.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert "fue cancelada" in respuesta
    assert final.cancel_draft is None


# ---------------------------------------------------------------------------
# (j) Draft de cancelar reemplaza al de agendar activo
# ---------------------------------------------------------------------------


def test_draft_de_cancelar_reemplaza_al_de_agendar(monkeypatch):
    crear_calls = []
    monkeypatch.setattr(
        tools,
        "crear_cita_desde_draft",
        lambda draft: crear_calls.append(draft) or {"ok": True, "cita_id": "x"},
    )
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    _mockear_citas_activas(monkeypatch, [_cita_activa()])
    orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
    conversation_id = "reemplazo-de-draft"
    state = _state_listo(orchestrator, conversation_id, "agendar", _booking_draft())

    # El scheduling agent propone cancelar: el draft nuevo reemplaza al anterior.
    turn_context = TurnContext(conversation_id, USUARIO, state)
    turn_context.set_draft(_cancel_draft(), "cancelar")
    assert state.booking_draft is None
    assert state.cancel_draft is not None
    assert state.pending_action == "cancelar"

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert len(cancel_calls) == 1
    assert crear_calls == []
    assert "fue cancelada" in respuesta
    assert state.cancel_draft is None


# ---------------------------------------------------------------------------
# (k) cita_id vacio o usuario distinto: nunca ejecutan y limpian el draft
# ---------------------------------------------------------------------------


def test_cita_id_vacio_nunca_se_ejecuta_y_se_limpia(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    verificaciones = _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "cita-id-vacio"
    state = _state_listo(
        orchestrator, conversation_id, "cancelar", _cancel_draft(cita_id="")
    )

    respuesta, state = asyncio.run(
        orchestrator.process(conversation_id, "sí", [], usuario_id=USUARIO)
    )
    assert cancel_calls == []
    assert verificaciones == []
    assert state.cancel_draft is None
    assert state.pending_action is None
    # El mensaje paso al agente (el draft corrupto se limpio).
    assert agent.calls == 1


def test_usuario_distinto_no_ejecuta_y_limpia(monkeypatch):
    cancel_calls = _mockear_ejecutor(
        monkeypatch, "ejecutar_cancelacion_desde_draft", [{"ok": True}]
    )
    verificaciones = _mockear_citas_activas(monkeypatch, [_cita_activa()])
    agent = _FakeAgent()
    orchestrator = Orchestrator(_FakeAgent(), agent)
    conversation_id = "usuario-distinto"
    state = _state_listo(orchestrator, conversation_id, "cancelar", _cancel_draft())

    respuesta, state = asyncio.run(
        orchestrator.process(
            conversation_id, "sí", [], usuario_id=str(uuid4())
        )
    )
    assert cancel_calls == []
    assert verificaciones == []
    assert state.cancel_draft is None
    assert state.pending_action is None
    assert agent.calls == 1
