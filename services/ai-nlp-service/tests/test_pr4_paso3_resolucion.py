"""PR4 paso 3: helpers de resolucion de citas por referencia textual.

Con httpx mockeado (sin servicios reales y sin LLM):
- 1 coincidencia resuelve (fecha fija: hoy=2026-10-31, 'lunes' = 2026-11-02).
- 2 o mas coincidencias piden aclaracion SIN ids en la salida.
- 0 coincidencias -> vacio.
- sin usuario verificado -> error y CERO llamadas HTTP.
- el GET siempre usa el usuario verificado.
"""

import json
import re
from datetime import date
from uuid import uuid4

from app.agents import tools

HOY = date(2026, 10, 31)  # sabado -> el lunes de la semana siguiente es 2026-11-02
LUNES = "2026-11-02"

UUID_REGEX = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)

USUARIO_VERIFICADO = str(uuid4())


def _cita(fecha, hora, medico_id, *, estado="programada"):
    return {
        "cita_id": str(uuid4()),
        "usuario_id": USUARIO_VERIFICADO,
        "medico_id": str(medico_id),
        "especialidad_id": "e1",
        "tipo_servicio": "medicina_general",
        "fecha_cita": fecha,
        "hora_inicio": f"{hora}:00",
        "hora_fin": f"{hora}:30",
        "sede_id": "s1",
        "estado": estado,
    }


class _Respuesta:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def _mockear_http(monkeypatch, payload):
    """Mockea el GET de /citas/usuario y devuelve la lista de URLs llamadas."""
    urls = []

    class _Client:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get(self, url, params=None, headers=None):
            urls.append(url)
            return _Respuesta(200, payload)

    monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
    monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")
    return urls


def _mockear_catalogo(monkeypatch, medicos=None, sedes=None, especialidades=None):
    def cached(endpoint, params=None):
        if endpoint.startswith("/medicos/"):
            medico_id = endpoint.rsplit("/", 1)[-1]
            return {"ok": True, "data": (medicos or {}).get(medico_id, {})}
        if endpoint == "/sedes":
            return {"ok": True, "data": sedes or []}
        if endpoint == "/especialidades":
            return {"ok": True, "data": especialidades or []}
        return {"ok": False, "error": "desconocido"}

    monkeypatch.setattr(tools, "_consultar_catalog_service_cached", cached)


def _catalogo_basico(monkeypatch, medico_id):
    _mockear_catalogo(
        monkeypatch,
        medicos={str(medico_id): {"nombres": "Ana", "apellidos": "Gomez"}},
        sedes=[{"sede_id": "s1", "nombre": "Sede Norte"}],
        especialidades=[{"especialidad_id": "e1", "nombre": "Medicina General"}],
    )


# --- normalizacion (regresion del error historico de join por caracteres) ---


def test_normalizar_conserva_espacios():
    # Conserva los espacios internos tal cual (el error historico fue
    # unir por caracteres); solo quita tildes y baja a minusculas.
    assert tools._normalizar_texto("Medicina General") == "medicina general"
    assert tools._normalizar_texto("Miércoles  Móvil") == "miercoles  movil"


def test_fecha_legible_en_espanol():
    assert tools._fecha_legible(LUNES) == "lunes 02/11/2026"


# --- resolucion ---


def test_una_cita_resuelve_por_dia_de_semana(monkeypatch):
    medico_id = uuid4()
    cita = _cita(LUNES, "08", medico_id)
    _mockear_http(monkeypatch, [cita])
    _catalogo_basico(monkeypatch, medico_id)

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert resultado["ok"] is True
    assert resultado["encontrada"] is True
    assert resultado["cita"]["cita_id"] == cita["cita_id"]
    assert resultado["cita"]["medico_nombre"] == "Ana Gomez"
    assert resultado["cita"]["sede_nombre"] == "Sede Norte"
    assert resultado["cita"]["especialidad_nombre"] == "Medicina General"


def test_dos_citas_el_mismo_dia_piden_aclaracion(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)])
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert resultado["ok"] is True
    assert resultado["encontrada"] is False
    assert "cita" not in resultado
    assert len(resultado["candidatas"]) == 2
    assert resultado["candidatas"][0]["fecha"] == "lunes 02/11/2026"


def test_dos_restricciones_acumulativas_elegirian_una_sola(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(
        monkeypatch,
        [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)],
    )
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario(
        "la del lunes de las 10:00", USUARIO_VERIFICADO, HOY
    )

    assert resultado["encontrada"] is True
    assert str(resultado["cita"]["hora_inicio"]).startswith("10:00")


def test_cero_coincidencias_devuelve_vacio(monkeypatch):
    _mockear_http(monkeypatch, [_cita(LUNES, "08", uuid4())])
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("del martes", USUARIO_VERIFICADO, HOY)

    assert resultado["ok"] is True
    assert resultado["encontrada"] is False
    assert resultado["candidatas"] == []


def test_dia_fuera_de_la_ventana_de_14_dias_no_coincide(monkeypatch):
    # lunes 2026-11-16 esta a 16 dias de hoy (2026-10-31): fuera de ventana.
    _mockear_http(monkeypatch, [_cita("2026-11-16", "08", uuid4())])
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is False
    assert resultado["candidatas"] == []


def test_referencia_vacia_con_varias_citas_aclara_no_elige_la_primera(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita("2026-11-05", "09", m2)])
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario("", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is False
    assert len(resultado["candidatas"]) == 2


def test_referencia_vacia_con_una_sola_cita_resuelve(monkeypatch):
    _mockear_http(monkeypatch, [_cita(LUNES, "08", uuid4())])
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is True


def test_fragmento_de_medico_filtra(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)])
    _mockear_catalogo(
        monkeypatch,
        medicos={
            str(m1): {"nombres": "Ana", "apellidos": "Gomez"},
            str(m2): {"nombres": "Luis", "apellidos": "Perez"},
        },
        sedes=[{"sede_id": "s1", "nombre": "Sede Norte"}],
        especialidades=[{"especialidad_id": "e1", "nombre": "Medicina General"}],
    )

    resultado = tools._resolver_cita_usuario("la de gomez", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is True
    assert resultado["cita"]["medico_id"] == str(m1)
    assert resultado["cita"]["medico_nombre"] == "Ana Gomez"


def test_citas_no_programadas_se_excluyen(monkeypatch):
    _mockear_http(
        monkeypatch,
        [
            _cita(LUNES, "08", uuid4(), estado="cancelada"),
            _cita(LUNES, "10", uuid4(), estado="atendida"),
        ],
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is False
    assert resultado["candidatas"] == []


def test_sin_usuario_verificado_falla_sin_llamadas_http(monkeypatch):
    urls = _mockear_http(monkeypatch, [])

    resultado = tools._resolver_cita_usuario("la del lunes", None, HOY)

    assert resultado["ok"] is False
    assert urls == []


def test_el_get_usa_siempre_el_usuario_verificado(monkeypatch):
    urls = _mockear_http(monkeypatch, [_cita(LUNES, "08", uuid4())])
    _catalogo_basico(monkeypatch, uuid4())

    tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert urls == [f"http://citas/citas/usuario/{USUARIO_VERIFICADO}"]


def test_salida_de_aclaracion_no_contiene_ningun_uuid(monkeypatch):
    _mockear_http(
        monkeypatch, [_cita(LUNES, "08", uuid4()), _cita(LUNES, "10", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)
    serializado = json.dumps(resultado, ensure_ascii=False)

    assert not UUID_REGEX.search(serializado), f"UUID filtrado hacia el LLM: {serializado}"
    assert "cita_id" not in serializado
    assert "usuario_id" not in serializado


# --- Correcciones del paso 3: fragmentos no bloqueantes, fechas relativas,
#     horas expresadas de varias formas, isinstance(lista) y tests de fechas ---


MANANA = "2026-11-01"  # hoy (2026-10-31) + 1


def test_cancelar_manana_con_fragmento_que_no_coincide_no_vacia(monkeypatch):
    # "medica" no es substring de "medicina": los fragmentos NO vacian el
    # resultado; la fecha relativa "manana" decide sola.
    medico_id = uuid4()
    _mockear_http(monkeypatch, [_cita(MANANA, "09", medico_id)])
    _catalogo_basico(monkeypatch, medico_id)

    resultado = tools._resolver_cita_usuario(
        "cancela mañana mi cita médica", USUARIO_VERIFICADO, HOY
    )

    assert resultado["ok"] is True
    assert resultado["encontrada"] is True
    assert resultado["cita"]["fecha_cita"] == MANANA


def test_fragmento_inexistente_no_vacia_el_resultado(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita("2026-11-05", "09", m2)])
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario("la de zzzz", USUARIO_VERIFICADO, HOY)

    # Sin el fragmento quedan 2: se ignoran los fragmentos y se aclara.
    assert resultado["encontrada"] is False
    assert len(resultado["candidatas"]) == 2


def test_hora_ambigua_sin_am_pm_resuelve_si_una_lectura_coincide(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)])
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario("la de las 10", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is True
    assert str(resultado["cita"]["hora_inicio"]).startswith("10:00")
    assert resultado["cita"]["medico_id"] == str(m2)


def test_hora_ambigua_sin_coincidencias_da_vacio(monkeypatch):
    # "las 10" (10:00 u 22:00) con una unica cita a las 08:00: NINGUNA lectura
    # coincide -> 0 candidatas (antes resolvia la de las 08:00, que no pidio).
    _mockear_http(monkeypatch, [_cita(LUNES, "08", uuid4())])
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la de las 10", USUARIO_VERIFICADO, HOY)

    assert resultado["ok"] is True
    assert resultado["encontrada"] is False
    assert resultado["candidatas"] == []


def test_hora_ambigua_con_dos_lecturas_que_coinciden_no_restringe(monkeypatch):
    # "las 7" = 07:00 u 19:00; si las DOS coinciden no se puede decidir:
    # no se restringe por hora y se pide aclaracion.
    _mockear_http(
        monkeypatch, [_cita(LUNES, "07", uuid4()), _cita(LUNES, "19", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la de las 7", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is False
    assert len(resultado["candidatas"]) == 2


def test_hora_con_meridiano_y_sin_minutos_es_nivel_de_hora(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)])
    _catalogo_basico(monkeypatch, m1)

    # "10 de la mañana" (sin :MM): la cita 10:00 sigue estando en esa hora.
    resultado = tools._resolver_cita_usuario(
        "la del lunes 10 de la mañana", USUARIO_VERIFICADO, HOY
    )

    assert resultado["encontrada"] is True
    assert str(resultado["cita"]["hora_inicio"]).startswith("10:00")


def test_hora_con_am_reconocida(monkeypatch):
    m1, m2 = uuid4(), uuid4()
    _mockear_http(monkeypatch, [_cita(LUNES, "08", m1), _cita(LUNES, "10", m2)])
    _catalogo_basico(monkeypatch, m1)

    resultado = tools._resolver_cita_usuario(
        "la del lunes de las 10am", USUARIO_VERIFICADO, HOY
    )

    assert resultado["encontrada"] is True
    assert str(resultado["cita"]["hora_inicio"]).startswith("10:00")


def test_fecha_iso_restringe(monkeypatch):
    _mockear_http(
        monkeypatch, [_cita(LUNES, "08", uuid4()), _cita("2026-11-05", "09", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario(
        "cancela la cita del 2026-11-05", USUARIO_VERIFICADO, HOY
    )

    assert resultado["encontrada"] is True
    assert resultado["cita"]["fecha_cita"] == "2026-11-05"


def test_fecha_dd_mm_restringe(monkeypatch):
    _mockear_http(
        monkeypatch, [_cita(LUNES, "08", uuid4()), _cita("2026-11-05", "09", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    # 05/11 sin anio: hoy es 2026-10-31 -> 05/11/2026 (aun no paso).
    resultado = tools._resolver_cita_usuario("la del 05/11", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is True
    assert resultado["cita"]["fecha_cita"] == "2026-11-05"


def test_hoy_resuelve_solo_la_cita_de_hoy(monkeypatch):
    hoy_cita = "2026-10-31"
    _mockear_http(
        monkeypatch, [_cita(hoy_cita, "08", uuid4()), _cita(MANANA, "09", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario("la de hoy", USUARIO_VERIFICADO, HOY)

    assert resultado["encontrada"] is True
    assert resultado["cita"]["fecha_cita"] == hoy_cita


def test_pasado_manana_resuelve_la_cita_de_dos_dias(monkeypatch):
    pasado = "2026-11-02"
    _mockear_http(
        monkeypatch, [_cita(MANANA, "09", uuid4()), _cita(pasado, "10", uuid4())]
    )
    _catalogo_basico(monkeypatch, uuid4())

    resultado = tools._resolver_cita_usuario(
        "cancela la de pasado mañana", USUARIO_VERIFICADO, HOY
    )

    assert resultado["encontrada"] is True
    assert resultado["cita"]["fecha_cita"] == pasado


def test_respuesta_200_con_dict_de_error_no_crashea(monkeypatch):
    _mockear_http(monkeypatch, {"detail": "error inesperado"})

    resultado = tools._resolver_cita_usuario("la del lunes", USUARIO_VERIFICADO, HOY)

    assert resultado["ok"] is False
    assert "error" in resultado
