"""PR4 paso 4: ejecutores de cancelar/reagendar desde draft (httpx mockeado).

Sin servicios reales y sin LLM. Cubre: 200 ok; 404 (cita ajena/inexistente);
detalle de "solo programada" => ya_cancelada; cupo ocupado; timeout; 500;
cita_id vacio => cero llamadas HTTP; header X-User-ID = usuario verificado y
cita_id tomado del draft; ninguna salida contiene UUID.
"""

import json
import re
from uuid import uuid4

from app.agents import tools
from app.core.conversation_state import CancelDraft, RescheduleDraft

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

USUARIO_VERIFICADO = str(uuid4())


class _Respuesta:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def _mockear_post(monkeypatch, respuesta=None, excepcion=None):
    """Mockea el POST del servicio de citas; devuelve la lista de llamadas."""
    llamadas = []

    class _Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def post(self, url, json=None, headers=None):
            llamadas.append({"url": url, "json": json, "headers": headers})
            if excepcion is not None:
                raise excepcion
            return respuesta

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")
    return llamadas


def _cancel_draft(cita_id=None):
    return CancelDraft(
        cita_id=str(uuid4()) if cita_id is None else cita_id,
        usuario_id=USUARIO_VERIFICADO,
        fecha="2026-11-02",
        hora_inicio="10:00",
        hora_fin="10:30",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gomez",
        sede_id="s1",
        sede_nombre="Sede Norte",
        especialidad_nombre="Medicina General",
        motivo="cambio de planes",
    )


def _reschedule_draft(cita_id=None):
    return RescheduleDraft(
        cita_id=str(uuid4()) if cita_id is None else cita_id,
        usuario_id=USUARIO_VERIFICADO,
        fecha_original="2026-11-02",
        hora_inicio_original="10:00",
        hora_fin_original="10:30",
        medico_id=str(uuid4()),
        medico_nombre="Ana Gomez",
        sede_id="s1",
        sede_nombre="Sede Norte",
        especialidad_nombre="Medicina General",
        nueva_fecha="2026-11-05",
        nueva_hora_inicio="08:00",
        nueva_hora_fin="08:30",
    )


# --- ejecutar_cancelacion_desde_draft ---


def test_cancelar_200_ok_usa_draft_y_usuario_verificado(monkeypatch):
    draft = _cancel_draft()
    llamadas = _mockear_post(monkeypatch, _Respuesta(200, {"cita_id": draft.cita_id}))

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado == {"ok": True}
    assert len(llamadas) == 1
    assert llamadas[0]["url"] == f"http://citas/citas/{draft.cita_id}/cancelar"
    assert llamadas[0]["headers"]["X-User-ID"] == USUARIO_VERIFICADO
    assert llamadas[0]["json"]["motivo"] == "cambio de planes"


def test_cancelar_404_falla_sin_uuid_en_la_salida(monkeypatch):
    draft = _cancel_draft()
    ajena = str(uuid4())
    llamadas = _mockear_post(
        monkeypatch, _Respuesta(404, {"detail": f"No existe cita con id {ajena}"})
    )

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert "ya_cancelada" not in resultado
    serializado = json.dumps(resultado, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
    assert ajena not in serializado
    assert len(llamadas) == 1


def test_cancelar_ya_no_programada_es_idempotente(monkeypatch):
    draft = _cancel_draft()
    _mockear_post(
        monkeypatch,
        _Respuesta(
            400, {"detail": "Solo se puede cancelar una cita en estado 'programada'"}
        ),
    )

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is True
    assert resultado["ya_cancelada"] is True


def test_cancelar_timeout_falla_sin_tocar_el_draft(monkeypatch):
    draft = _cancel_draft()
    _mockear_post(monkeypatch, excepcion=tools.httpx.TimeoutException("timeout"))

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert "error" in resultado
    assert "ya_cancelada" not in resultado
    # El draft queda intacto (el executor no lo modifica).
    assert draft.cita_id and draft.motivo == "cambio de planes"


def test_cancelar_500_falla_sin_banderas(monkeypatch):
    draft = _cancel_draft()
    _mockear_post(monkeypatch, _Respuesta(500, {"detail": "boom"}))

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert "ya_cancelada" not in resultado
    assert "cita_cambio" not in resultado
    assert "cupo_no_disponible" not in resultado


def test_cancelar_cita_id_vacio_no_llama_http(monkeypatch):
    draft = _cancel_draft(cita_id="")
    llamadas = _mockear_post(monkeypatch, _Respuesta(200, {}))

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert llamadas == []


def test_cancelar_sin_usuario_verificado_no_llama_http(monkeypatch):
    draft = _cancel_draft()
    llamadas = _mockear_post(monkeypatch, _Respuesta(200, {}))

    resultado = tools.ejecutar_cancelacion_desde_draft(draft, "")

    assert resultado["ok"] is False
    assert llamadas == []


# --- ejecutar_reagendamiento_desde_draft ---


def test_reprogramar_200_ok_payload_y_header(monkeypatch):
    draft = _reschedule_draft()
    llamadas = _mockear_post(monkeypatch, _Respuesta(200, {"cita_id": draft.cita_id}))

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado == {"ok": True}
    assert len(llamadas) == 1
    assert llamadas[0]["url"] == f"http://citas/citas/{draft.cita_id}/reprogramar"
    assert llamadas[0]["headers"]["X-User-ID"] == USUARIO_VERIFICADO
    assert llamadas[0]["json"] == {
        "nueva_fecha": "2026-11-05",
        "nueva_hora_inicio": "08:00",
        "nueva_hora_fin": "08:30",
    }


def test_reprogramar_cupo_ocupado(monkeypatch):
    draft = _reschedule_draft()
    _mockear_post(
        monkeypatch,
        _Respuesta(
            400, {"detail": "El medico ya tiene una cita programada en el nuevo horario"}
        ),
    )

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert resultado["cupo_no_disponible"] is True
    assert "cita_cambio" not in resultado
    assert not UUID_REGEX.search(json.dumps(resultado, ensure_ascii=False))


def test_reprogramar_404_cita_ajena_o_inexistente_es_cita_cambio(monkeypatch):
    draft = _reschedule_draft()
    ajena = str(uuid4())
    _mockear_post(
        monkeypatch, _Respuesta(404, {"detail": f"No existe cita con id {ajena}"})
    )

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert resultado["cita_cambio"] is True
    assert "cupo_no_disponible" not in resultado
    serializado = json.dumps(resultado, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
    assert ajena not in serializado


def test_reprogramar_cita_ya_no_programada_es_cita_cambio(monkeypatch):
    draft = _reschedule_draft()
    _mockear_post(
        monkeypatch,
        _Respuesta(
            400, {"detail": "Solo se puede reprogramar una cita en estado 'programada'"}
        ),
    )

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert resultado["cita_cambio"] is True


def test_reprogramar_timeout_fallo_transitorio_sin_banderas(monkeypatch):
    draft = _reschedule_draft()
    _mockear_post(monkeypatch, excepcion=tools.httpx.TimeoutException("timeout"))

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert "error" in resultado
    assert "cupo_no_disponible" not in resultado
    assert "cita_cambio" not in resultado


def test_reprogramar_500_fallo_transitorio_sin_banderas(monkeypatch):
    draft = _reschedule_draft()
    _mockear_post(monkeypatch, _Respuesta(500, {"detail": "boom"}))

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert "cupo_no_disponible" not in resultado
    assert "cita_cambio" not in resultado


def test_reprogramar_cita_id_vacio_no_llama_http(monkeypatch):
    draft = _reschedule_draft(cita_id="")
    llamadas = _mockear_post(monkeypatch, _Respuesta(200, {}))

    resultado = tools.ejecutar_reagendamiento_desde_draft(draft, USUARIO_VERIFICADO)

    assert resultado["ok"] is False
    assert llamadas == []


def test_ninguna_salida_de_los_ejecutores_contiene_uuid(monkeypatch):
    draft = _cancel_draft()
    salidas = []

    for respuesta, executor, d in [
        (_Respuesta(200, {}), tools.ejecutar_cancelacion_desde_draft, draft),
        (
            _Respuesta(404, {"detail": f"No existe cita con id {uuid4()}"}),
            tools.ejecutar_cancelacion_desde_draft,
            draft,
        ),
        (
            _Respuesta(
                400,
                {"detail": "Solo se puede cancelar una cita en estado 'programada'"},
            ),
            tools.ejecutar_cancelacion_desde_draft,
            draft,
        ),
        (
            _Respuesta(400, {"detail": "El medico ya tiene una cita programada en el nuevo horario"}),
            tools.ejecutar_reagendamiento_desde_draft,
            _reschedule_draft(),
        ),
        (
            _Respuesta(404, {"detail": f"No existe cita con id {uuid4()}"}),
            tools.ejecutar_reagendamiento_desde_draft,
            _reschedule_draft(),
        ),
    ]:
        _mockear_post(monkeypatch, respuesta)
        salidas.append(executor(d, USUARIO_VERIFICADO))

    for salida in salidas:
        serializado = json.dumps(salida, ensure_ascii=False)
        assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
        assert "cita_id" not in serializado
        assert "usuario_id" not in serializado
