"""PR4 paso 5: tools proponer_cancelacion / proponer_reagendamiento.

Con httpx mockeado (sin servicios reales y sin LLM):
- exito: draft correcto via set_draft y salida MINIMA sin UUID ni cita_id.
- 0 o varias coincidencias: sin draft (aclaracion sin ids).
- cupo nuevo inexistente u otra sede (reagendar): sin draft, mensaje claro
  que menciona la sede de la cita.
- reagendar valida ANTES de cualquier HTTP: formato YYYY-MM-DD/HH:MM,
  fecha/hora futura en America/Bogota (ahora inyectada) y que no sea la
  misma fecha/hora de la cita.
- sin identidad: error y CERO llamadas HTTP.
- reemplaza un draft de agendar activo.
- SCHEDULING_TOOLS: fuera cancelar_cita/reagendar_cita, dentro las nuevas.
- hoy se calcula en America/Bogota (no date.today()).
- consultar_citas_usuario no expone NINGUN UUID (regex sobre el JSON).
"""

import json
import re
from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.agents import tools
from app.core.conversation_state import BookingDraft, ConversationState
from app.core.turn_context import TurnContext

HOY = date(2026, 10, 31)
LUNES = "2026-11-02"
JUEVES = "2026-11-05"
# Instante inyectado en los tests de validacion: HOY a las 10:00 en Bogota.
AHORA_TESTS = datetime(2026, 10, 31, 10, 0, tzinfo=ZoneInfo("America/Bogota"))

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

USUARIO_VERIFICADO = str(uuid4())


def _cita(fecha, hora, medico_id=None, *, sede_id="s1"):
    return {
        "cita_id": str(uuid4()),
        "usuario_id": USUARIO_VERIFICADO,
        "medico_id": str(medico_id or uuid4()),
        "especialidad_id": "e1",
        "tipo_servicio": "medicina_general",
        "fecha_cita": fecha,
        "hora_inicio": f"{hora}:00",
        "hora_fin": f"{hora}:30",
        "sede_id": sede_id,
        "estado": "programada",
    }


class _Respuesta:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def _mockear_http(monkeypatch, *, usuario_citas=None, slots=None, slots_status=200):
    """GET /citas/usuario/{id} -> usuario_citas; /slots-detallados -> slots."""
    llamadas = []

    class _Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, params=None, headers=None):
            llamadas.append({"url": url, "params": params, "headers": headers})
            if url.endswith("/citas/slots-detallados"):
                return _Respuesta(slots_status, slots if slots is not None else [])
            return _Respuesta(200, usuario_citas if usuario_citas is not None else [])

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")
    return llamadas


def _mockear_catalogo(monkeypatch, *, duracion=None):
    """Catalogo con "Ana Gomez", "Sede Norte" y especialidad e1 (duracion opcional)."""
    especialidades = [{"especialidad_id": "e1", "nombre": "Medicina General"}]
    if duracion is not None:
        especialidades[0]["duracion_cita_minutos"] = duracion

    def cached(endpoint, params=None):
        if endpoint.startswith("/medicos/"):
            return {"ok": True, "data": {"nombres": "Ana", "apellidos": "Gomez"}}
        if endpoint == "/sedes":
            return {"ok": True, "data": [{"sede_id": "s1", "nombre": "Sede Norte"}]}
        if endpoint == "/especialidades":
            return {"ok": True, "data": especialidades}
        return {"ok": False, "error": "desconocido"}

    monkeypatch.setattr(tools, "_consultar_catalog_service_cached", cached)


def _contexto(state=None):
    state = state or ConversationState()
    turn_context = TurnContext("conv-1", USUARIO_VERIFICADO, state)
    context = SimpleNamespace(
        invocation_state={"turn_context": turn_context, "state": state}
    )
    return context, state


def _mockear_ahora(monkeypatch, ahora=AHORA_TESTS):
    """Inyecta el reloj de America/Bogota usado por las tools de propuesta."""
    monkeypatch.setattr(tools, "_ahora_bogota", lambda: ahora)


def _assert_salida_minima(datos, accion):
    assert datos == {"ok": True, "propuesta_creada": True, "accion": accion}
    serializado = json.dumps(datos, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
    assert "cita_id" not in serializado
    assert "usuario_id" not in serializado


# --- proponer_cancelacion ---


def test_cancelacion_exito_crea_draft_y_salida_minima(monkeypatch):
    cita = _cita(LUNES, "08")
    _mockear_http(monkeypatch, usuario_citas=[cita])
    _mockear_catalogo(monkeypatch)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_cancelacion("la del lunes", tool_context=context)
    )

    _assert_salida_minima(datos, "cancelar")
    assert state.pending_action == "cancelar"
    assert state.pending_confirmation is True
    draft = state.cancel_draft
    assert draft.cita_id == cita["cita_id"]
    assert draft.usuario_id == USUARIO_VERIFICADO
    assert draft.fecha == LUNES
    assert draft.hora_inicio == "08:00"
    assert draft.hora_fin == "08:30"
    assert draft.medico_nombre == "Ana Gomez"
    assert draft.sede_id == "s1"
    assert draft.sede_nombre == "Sede Norte"
    assert draft.especialidad_nombre == "Medicina General"
    assert state.booking_draft is None
    assert state.reschedule_draft is None


def test_cancelacion_varias_coincidencias_sin_draft(monkeypatch):
    _mockear_http(
        monkeypatch,
        usuario_citas=[_cita(LUNES, "08"), _cita(JUEVES, "10")],
    )
    _mockear_catalogo(monkeypatch)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_cancelacion("la cita", tool_context=context)
    )

    assert datos["ok"] is True
    assert datos["encontrada"] is False
    assert len(datos["candidatas"]) == 2
    serializado = json.dumps(datos, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
    assert "cita_id" not in serializado
    assert state.cancel_draft is None
    assert state.pending_action is None


def test_cancelacion_sin_coincidencias_sin_draft(monkeypatch):
    _mockear_http(monkeypatch, usuario_citas=[_cita(LUNES, "08")])
    _mockear_catalogo(monkeypatch)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_cancelacion("la del martes", tool_context=context)
    )

    assert datos["ok"] is True
    assert datos["encontrada"] is False
    assert datos["candidatas"] == []
    assert state.cancel_draft is None
    assert state.pending_action is None


# --- proponer_reagendamiento ---


def test_reagendamiento_exito_crea_draft_con_duracion_del_catalogo(monkeypatch):
    cita = _cita(LUNES, "08")
    slots = [
        {
            "medico_id": cita["medico_id"],
            "sede_id": "s1",
            "especialidad_id": "e1",
            "hora_inicio": "15:00",
            "hora_fin": "15:20",
        }
    ]
    llamadas = _mockear_http(monkeypatch, usuario_citas=[cita], slots=slots)
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", JUEVES, "15:00", tool_context=context
        )
    )

    _assert_salida_minima(datos, "reagendar")
    assert state.pending_action == "reagendar"
    draft = state.reschedule_draft
    assert draft.cita_id == cita["cita_id"]
    assert draft.usuario_id == USUARIO_VERIFICADO
    # Originales de la cita y nuevas desde el LLM.
    assert draft.fecha_original == LUNES
    assert draft.hora_inicio_original == "08:00"
    assert draft.hora_fin_original == "08:30"
    assert draft.medico_nombre == "Ana Gomez"
    assert draft.sede_nombre == "Sede Norte"
    assert draft.nueva_fecha == JUEVES
    assert draft.nueva_hora_inicio == "15:00"
    # hora_fin = hora + duracion_cita_minutos del catalogo (20), no 30 fijos.
    assert draft.nueva_hora_fin == "15:20"
    assert state.cancel_draft is None
    assert state.booking_draft is None

    # El cupo se valido contra slots-detallados del MEDICO de la cita.
    consulta = next(
        llamada
        for llamada in llamadas
        if llamada["url"].endswith("/citas/slots-detallados")
    )
    assert consulta["params"] == {"medico_id": cita["medico_id"], "fecha": JUEVES}


def test_reagendamiento_fallback_30_cuando_el_catalogo_no_da_duracion(monkeypatch):
    cita = _cita(LUNES, "08")
    slots = [{"medico_id": cita["medico_id"], "sede_id": "s1", "hora_inicio": "15:00"}]
    _mockear_http(monkeypatch, usuario_citas=[cita], slots=slots)
    _mockear_catalogo(monkeypatch)  # especialidad sin duracion_cita_minutos
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", JUEVES, "15:00", tool_context=context
        )
    )

    assert datos["ok"] is True
    assert state.reschedule_draft.nueva_hora_fin == "15:30"


def test_reagendamiento_cupo_inexistente_sin_draft(monkeypatch):
    cita = _cita(LUNES, "08")
    _mockear_http(monkeypatch, usuario_citas=[cita], slots=[])  # sin cupos ese dia
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", JUEVES, "15:00", tool_context=context
        )
    )

    assert datos["ok"] is False
    assert "cupo" in datos["error"].lower()
    assert JUEVES in datos["error"]
    assert "15:00" in datos["error"]
    # El mensaje aclara que el cupo se busca en la sede de la cita.
    assert "sede de tu cita" in datos["error"]
    assert "Sede Norte" in datos["error"]
    serializado = json.dumps(datos, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado)
    assert state.reschedule_draft is None
    assert state.pending_action is None


def test_reagendamiento_cupo_en_otra_sede_no_cuenta(monkeypatch):
    # El medico esta libre a las 15:00 pero en OTRA sede: reprogramar
    # conserva la sede original, asi que ese cupo no sirve.
    cita = _cita(LUNES, "08", sede_id="s1")
    slots = [{"medico_id": cita["medico_id"], "sede_id": "s2", "hora_inicio": "15:00"}]
    _mockear_http(monkeypatch, usuario_citas=[cita], slots=slots)
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", JUEVES, "15:00", tool_context=context
        )
    )

    assert datos["ok"] is False
    assert state.reschedule_draft is None


def test_reagendamiento_varias_coincidencias_sin_draft(monkeypatch):
    _mockear_http(
        monkeypatch,
        usuario_citas=[_cita(LUNES, "08"), _cita(JUEVES, "08")],
        slots=[{"sede_id": "s1", "hora_inicio": "15:00"}],
    )
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la de las 8", JUEVES, "15:00", tool_context=context
        )
    )

    assert datos["encontrada"] is False
    assert "candidatas" in datos
    assert state.reschedule_draft is None


# --- validacion de fecha/hora nuevas (antes de cualquier HTTP) ---


def test_reagendamiento_fecha_pasada_rechazada_sin_http(monkeypatch):
    _mockear_ahora(monkeypatch)  # AHORA_TESTS = 2026-10-31 10:00 Bogota
    llamadas = _mockear_http(monkeypatch)
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", "2026-10-30", "15:00", tool_context=context
        )
    )

    assert datos["ok"] is False
    assert "ya paso" in datos["error"]
    assert "2026-10-30" in datos["error"]
    assert llamadas == []  # ni consulta de citas ni de slots
    assert state.reschedule_draft is None
    assert state.pending_action is None


def test_reagendamiento_hora_pasada_hoy_rechazada_sin_http(monkeypatch):
    _mockear_ahora(monkeypatch)  # 2026-10-31 10:00 Bogota
    llamadas = _mockear_http(monkeypatch)
    context, state = _contexto()

    # Hora anterior a las 10:00 y hora exactamente igual a las 10:00:
    # ninguna es futura.
    for hora in ["09:00", "10:00"]:
        datos = json.loads(
            tools.proponer_reagendamiento(
                "la del lunes", "2026-10-31", hora, tool_context=context
            )
        )
        assert datos["ok"] is False
        assert "ya paso" in datos["error"]
        assert "10:00" in datos["error"]

    assert llamadas == []
    assert state.reschedule_draft is None


def test_reagendamiento_hoy_mas_tarde_si_es_valida(monkeypatch):
    # Mismo dia, hora posterior al reloj inyectado: futura en Bogota.
    _mockear_ahora(monkeypatch)
    cita = _cita(LUNES, "08")
    slots = [{"medico_id": cita["medico_id"], "sede_id": "s1", "hora_inicio": "15:00"}]
    _mockear_http(monkeypatch, usuario_citas=[cita], slots=slots)
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", "2026-10-31", "15:00", tool_context=context
        )
    )

    assert datos["propuesta_creada"] is True
    assert state.reschedule_draft.nueva_fecha == "2026-10-31"


def test_reagendamiento_formato_invalido_rechazado_sin_http(monkeypatch):
    _mockear_ahora(monkeypatch)
    llamadas = _mockear_http(monkeypatch)
    context, state = _contexto()

    casos = [
        ("manana", "15:00", "formato YYYY-MM-DD"),
        ("2026-11-5", "15:00", "formato YYYY-MM-DD"),
        ("2026-13-01", "15:00", "fecha valida"),
        (JUEVES, "9:00", "formato HH:MM"),
        (JUEVES, "15h30", "formato HH:MM"),
        (JUEVES, "25:00", "hora valida"),
    ]
    for fecha, hora, esperado in casos:
        datos = json.loads(
            tools.proponer_reagendamiento(
                "la del lunes", fecha, hora, tool_context=context
            )
        )
        assert datos["ok"] is False, (fecha, hora)
        assert esperado in datos["error"], (fecha, hora, datos["error"])
        assert "propuesta_creada" not in datos

    assert llamadas == []
    assert state.reschedule_draft is None


def test_reagendamiento_a_la_misma_fecha_y_hora_rechazado(monkeypatch):
    cita = _cita(LUNES, "08")
    llamadas = _mockear_http(monkeypatch, usuario_citas=[cita])
    _mockear_catalogo(monkeypatch, duracion=20)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_reagendamiento(
            "la del lunes", LUNES, "08:00", tool_context=context
        )
    )

    assert datos["ok"] is False
    assert "ya tienes esa cita" in datos["error"].lower()
    assert LUNES in datos["error"]
    assert "08:00" in datos["error"]
    serializado = json.dumps(datos, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado)
    # Resolvio la cita pero nunca consulto cupos ni guardo draft.
    assert not any(
        llamada["url"].endswith("/citas/slots-detallados") for llamada in llamadas
    )
    assert state.reschedule_draft is None
    assert state.pending_action is None


# --- identidad y estado ---


def test_sin_identidad_falla_sin_http(monkeypatch):
    def _explotar(**_kwargs):
        raise AssertionError("no debe crearse un cliente http sin identidad")

    monkeypatch.setattr(tools.httpx, "Client", _explotar)
    state = ConversationState()
    context = SimpleNamespace(
        invocation_state={
            "turn_context": TurnContext("conv-1", None, state),
            "state": state,
        }
    )

    for salida in [
        tools.proponer_cancelacion("la de mañana", tool_context=context),
        tools.proponer_reagendamiento(
            "la de mañana", JUEVES, "15:00", tool_context=context
        ),
    ]:
        assert "identidad autenticada" in salida
    assert state.cancel_draft is None
    assert state.reschedule_draft is None


def test_reemplaza_draft_de_agendar_activo(monkeypatch):
    state = ConversationState()
    state.booking_draft = BookingDraft(
        usuario_id=USUARIO_VERIFICADO,
        especialidad_id="e1",
        especialidad_nombre="Medicina General",
        medico_id=str(uuid4()),
        medico_nombre="Otro Medico",
        sede_id="s1",
        sede_nombre="Sede Norte",
        sede_direccion="Calle 1",
        tipo_servicio="medicina_general",
        fecha=LUNES,
        hora_inicio="09:00",
        hora_fin="09:30",
    )
    state.pending_action = "agendar"
    state.pending_confirmation = True

    cita = _cita(LUNES, "08")
    _mockear_http(monkeypatch, usuario_citas=[cita])
    _mockear_catalogo(monkeypatch)
    context, _state = _contexto(state)

    datos = json.loads(
        tools.proponer_cancelacion("la de las 8", tool_context=context)
    )

    assert datos["propuesta_creada"] is True
    assert state.booking_draft is None
    assert state.cancel_draft is not None
    assert state.cancel_draft.cita_id == cita["cita_id"]
    assert state.pending_action == "cancelar"


# --- reglas de superficie ---


def test_scheduling_tools_reemplaza_las_viejas():
    nombres = {herramienta.tool_name for herramienta in tools.SCHEDULING_TOOLS}
    assert "cancelar_cita" not in nombres
    assert "reagendar_cita" not in nombres
    assert "proponer_cancelacion" in nombres
    assert "proponer_reagendamiento" in nombres


def test_hoy_se_calcula_en_bogota(monkeypatch):
    class _FakeDateTime:
        zona = None

        @classmethod
        def now(cls, tz=None):
            cls.zona = tz
            # Instante real 2026-11-01 02:00 UTC = 2026-10-31 21:00 en Bogota;
            # datetime.now(ZoneInfo) devuelve la hora YA convertida a la zona
            # (en UTC seria "manana", en Bogota es HOY).
            return datetime(2026, 11, 1, 2, 0, tzinfo=timezone.utc).astimezone(tz)

        strptime = staticmethod(datetime.strptime)

    monkeypatch.setattr(tools, "datetime", _FakeDateTime)
    cita = _cita("2026-10-31", "08")
    _mockear_http(monkeypatch, usuario_citas=[cita])
    _mockear_catalogo(monkeypatch)
    context, state = _contexto()

    datos = json.loads(
        tools.proponer_cancelacion("la de hoy", tool_context=context)
    )

    assert datos["propuesta_creada"] is True
    assert state.cancel_draft.fecha == "2026-10-31"
    assert str(_FakeDateTime.zona) == "America/Bogota"


def test_consultar_citas_usuario_no_expone_uuids(monkeypatch):
    # Cita con la forma REAL de CitaResponse del backend: trae 5 UUIDs
    # (cita_id, usuario_id, medico_id, sede_id, especialidad_id).
    cita = _cita(LUNES, "08")
    cita["sede_id"] = str(uuid4())
    cita["especialidad_id"] = str(uuid4())
    cita["descripcion_sintomas"] = "Fiebre desde el lunes"
    cancelada = _cita(LUNES, "10")
    cancelada["estado"] = "cancelada"
    _mockear_http(monkeypatch, usuario_citas=[cita, cancelada])
    context, _state = _contexto()

    datos = json.loads(
        tools.consultar_citas_usuario.__wrapped__("ignorado", tool_context=context)
    )

    assert datos["ok"] is True
    assert datos["total"] == 1
    # Se conservan los campos legibles.
    assert datos["citas"][0]["fecha_cita"] == LUNES
    assert datos["citas"][0]["hora_inicio"] == "08:00"
    assert datos["citas"][0]["estado"] == "programada"
    # Ningun campo id llega al LLM...
    assert not (tools._CAMPOS_ID_PROHIBIDOS_LLM & set(datos["citas"][0]))
    # ...y ningun UUID aparece en toda la salida (regex sobre el JSON).
    serializado = json.dumps(datos, ensure_ascii=False)
    assert not UUID_REGEX.search(serializado), f"UUID filtrado: {serializado}"
