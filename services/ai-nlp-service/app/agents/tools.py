from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from datetime import date, datetime, timedelta
from threading import RLock
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from strands import tool
from strands.types.tools import ToolContext

from ..core.logger import log_event
from ..core.conversation_state import BookingDraft, CancelDraft, RescheduleDraft

CITAS_TIMEOUT_SECONDS = 4.0
CATALOG_CACHE_TTL_SECONDS = 10 * 60


class _TtlCache:
    """Cache process-local y thread-safe para respuestas de catalogo."""

    def __init__(self, ttl_seconds: float) -> None:
        self._ttl_seconds = ttl_seconds
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], tuple[float, Any]] = {}
        self._lock = RLock()

    def get(self, key: tuple[str, tuple[tuple[str, str], ...]]) -> Any | None:
        now = time.monotonic()
        with self._lock:
            cached = self._values.get(key)
            if cached is None:
                return None
            stored_at, value = cached
            if now - stored_at >= self._ttl_seconds:
                self._values.pop(key, None)
                return None
            return value

    def set(self, key: tuple[str, tuple[tuple[str, str], ...]], value: Any) -> None:
        with self._lock:
            self._values[key] = (time.monotonic(), value)

    def clear(self) -> None:
        with self._lock:
            self._values.clear()


_CATALOG_CACHE = _TtlCache(CATALOG_CACHE_TTL_SECONDS)


def _obtener_catalog_service_url() -> str | None:
    load_dotenv()
    return os.getenv("CATALOG_SERVICE_URL")


def _obtener_citas_service_url() -> str | None:
    load_dotenv()
    return os.getenv("CITAS_SERVICE_URL")


def _verified_usuario_id(tool_context: ToolContext | None) -> str | None:
    """Obtiene la identidad verificada por el orquestador, nunca la del LLM."""
    invocation_state = tool_context.invocation_state if tool_context else {}
    turn_context = invocation_state.get("turn_context")
    usuario_id = getattr(turn_context, "usuario_id", None)
    if not usuario_id:
        usuario_id = invocation_state.get("usuario_id")
    try:
        parsed = UUID(str(usuario_id))
    except (TypeError, ValueError):
        return None
    if parsed.int == 0:
        return None
    return str(parsed)


def _consultar_catalog_service(
    endpoint: str, params: dict | None = None
) -> dict[str, Any]:
    """Consulta al Catalog Service y retorna los datos."""
    catalog_url = _obtener_catalog_service_url()
    if not catalog_url:
        return {"ok": False, "error": "CATALOG_SERVICE_URL no configurado."}

    headers = {"Content-Type": "application/json"}
    log_event("TOOLS", "HTTP", "debug", f"Catalog GET {endpoint} params={params}")
    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{catalog_url}{endpoint}"
            if params:
                response = client.get(url, params=params, headers=headers)
            else:
                response = client.get(url, headers=headers)

            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                log_event("TOOLS", "HTTP", "debug", f"Catalog {endpoint} -> {response.status_code} ({elapsed}ms)")
                return {"ok": True, "data": response.json()}
            log_event("TOOLS", "HTTP", "warning", f"Catalog {endpoint} -> {response.status_code} ({elapsed}ms)")
            return {"ok": False, "error": "No pude obtener la informacion."}
    except httpx.TimeoutException:
        log_event("TOOLS", "TIMEOUT", "warning", f"Catalog {endpoint} timeout ({CITAS_TIMEOUT_SECONDS}s)")
        return {"ok": False, "error": "La consulta tardo demasiado."}
    except httpx.RequestError as exc:
        log_event("TOOLS", "ERROR", "error", f"Catalog {endpoint} conexion: {exc}")
        return {"ok": False, "error": "Problema de conexion."}
    except Exception as exc:
        log_event("TOOLS", "ERROR", "error", f"Catalog {endpoint} error: {exc}")
        return {"ok": False, "error": "Error inesperado."}


def _consultar_catalog_service_cached(
    endpoint: str, params: dict | None = None
) -> dict[str, Any]:
    """Consulta catalogo con TTL; no almacena respuestas fallidas."""
    normalized_params = tuple(
        sorted((str(key), str(value)) for key, value in (params or {}).items())
    )
    key = (endpoint, normalized_params)
    cached = _CATALOG_CACHE.get(key)
    if cached is not None:
        log_event("TOOLS", "CACHE", "debug", f"Catalog cache hit {endpoint} params={params}")
        return {"ok": True, "data": cached}

    result = _consultar_catalog_service(endpoint, params)
    if result.get("ok"):
        _CATALOG_CACHE.set(key, result.get("data"))
    return result


def _sumar_minutos_a_hora(hora_str: str, minutos: int) -> str:
    try:
        parts = hora_str.split(":")
        total = int(parts[0]) * 60 + int(parts[1]) + minutos
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"
    except (ValueError, AttributeError):
        return hora_str


@tool
def obtener_especialidades() -> str:
    """Lista todas las especialidades médicas disponibles en la EPS Digital.

    Returns:
        JSON con la lista de especialidades, cada una con: especialidad_id (UUID),
        nombre, descripcion, activa.
    """
    log_event("TOOLS", "EXEC", "info", "Ejecutando obtener_especialidades")
    result = _consultar_catalog_service_cached("/especialidades")
    if result.get("ok"):
        return json.dumps({
            "ok": True,
            "especialidades": result.get("data", []),
            "mensaje": "Estas son las especialidades disponibles.",
        }, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


@tool
def obtener_medicos(especialidad_id: str) -> str:
    """Lista los médicos disponibles para una especialidad específica.

    Args:
        especialidad_id: UUID de la especialidad médica (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).

    Returns:
        JSON con la lista de médicos, cada uno con: medico_id (UUID), nombre,
        apellido, especialidad, activo.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando obtener_medicos(especialidad_id={especialidad_id})")
    if not especialidad_id:
        return json.dumps({"ok": False, "error": "Necesito que especialidad queres."}, ensure_ascii=False)

    result = _consultar_catalog_service_cached(
        f"/especialidades/{especialidad_id}/medicos"
    )
    if result.get("ok"):
        return json.dumps({
            "ok": True,
            "medicos": result.get("data", []),
            "mensaje": "Aqui estan los medicos disponibles.",
        }, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


@tool
def obtener_sedes() -> str:
    """Lista las sedes/clínicas disponibles de la EPS Digital.

    Returns:
        JSON con la lista de sedes, cada una con: sede_id (UUID), nombre,
        direccion, telefono, activa.
    """
    log_event("TOOLS", "EXEC", "info", "Ejecutando obtener_sedes")
    result = _consultar_catalog_service_cached("/sedes")
    if result.get("ok"):
        return json.dumps({
            "ok": True,
            "sedes": result.get("data", []),
            "mensaje": "Estas son las sedes disponibles.",
        }, ensure_ascii=False)
    return json.dumps(result, ensure_ascii=False)


@tool
def obtener_disponibilidad_citas(especialidad_id: str, fecha: str) -> str:
    """Consulta horarios disponibles para una especialidad en una fecha específica.

    Args:
        especialidad_id: UUID de la especialidad médica (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
        fecha: Fecha en formato YYYY-MM-DD (ej: 2026-09-07).

    Returns:
        JSON con los slots de tiempo libres: cupos (lista de horas HH:MM),
        slots_completos (detalles), especialidad_id, fecha.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando obtener_disponibilidad_citas(especialidad_id={especialidad_id}, fecha={fecha})")

    if not especialidad_id or not fecha:
        return json.dumps({
            "ok": False,
            "error": "Necesito la especialidad y la fecha para buscar horarios.",
        }, ensure_ascii=False)

    catalog_url = _obtener_citas_service_url()
    if not catalog_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}
    log_event("TOOLS", "HTTP", "debug", f"Citas GET /citas/slots-disponibles params={{'especialidad_id': especialidad_id, 'fecha': fecha}}")
    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{catalog_url}/citas/slots-disponibles"
            response = client.get(url, params={"especialidad_id": especialidad_id, "fecha": fecha}, headers=headers)
            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                log_event("TOOLS", "HTTP", "debug", f"Citas /slots-disponibles -> {response.status_code} ({elapsed}ms)")
                slots_raw = response.json()
                cupos = [slot.get("hora_inicio", "") for slot in slots_raw if slot.get("hora_inicio")]
                return json.dumps({
                    "ok": True,
                    "tool": "obtener_disponibilidad_citas",
                    "especialidad_id": especialidad_id,
                    "fecha": fecha,
                    "cupos": cupos,
                    "slots_completos": slots_raw,
                    "mensaje": (
                        f"Encontre {len(cupos)} horarios disponibles para el {fecha}."
                        if cupos
                        else f"No hay horarios disponibles para el {fecha}."
                    ),
                }, ensure_ascii=False)
            log_event("TOOLS", "HTTP", "warning", f"Citas /slots-disponibles -> {response.status_code} ({elapsed}ms)")
            return json.dumps({"ok": False, "error": "No pude consultar la disponibilidad."}, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La consulta tardo demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexion."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado."}, ensure_ascii=False)


@tool
def buscar_opciones_cita(especialidad_id: str, fecha_desde: str = "") -> str:
    """Busca la primera disponibilidad futura con opciones completas.

    Args:
        especialidad_id: UUID de la especialidad médica.
        fecha_desde: Fecha inicial opcional en formato YYYY-MM-DD.
    """
    log_event(
        "TOOLS",
        "EXEC",
        "info",
        f"Ejecutando buscar_opciones_cita(especialidad_id={especialidad_id}, fecha_desde={fecha_desde})",
    )
    if not especialidad_id:
        return json.dumps({"ok": False, "error": "Necesito la especialidad para buscar disponibilidad."}, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    if fecha_desde:
        try:
            datetime.strptime(fecha_desde, "%Y-%m-%d")
        except ValueError:
            return json.dumps({"ok": False, "error": "fecha_desde debe tener formato YYYY-MM-DD."}, ensure_ascii=False)
    else:
        fecha_desde = datetime.now(ZoneInfo("America/Bogota")).date().isoformat()

    try:
        if not citas_url:
            return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{citas_url}/citas/proxima-disponibilidad",
                params={
                    "especialidad_id": especialidad_id,
                    "desde": fecha_desde,
                    "dias": 14,
                    "limite": 5,
                },
                headers={"Content-Type": "application/json"},
            )
        if not 200 <= response.status_code < 300:
            return json.dumps({"ok": False, "error": "No pude consultar la próxima disponibilidad."}, ensure_ascii=False)
        resultado = response.json()
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La consulta de disponibilidad tardó demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexión al consultar disponibilidad."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado al consultar disponibilidad."}, ensure_ascii=False)

    opciones = resultado.get("opciones", [])
    if not resultado.get("fecha") or not opciones:
        return json.dumps({
            "ok": True,
            "fecha": None,
            "opciones": [],
            "mensaje": f"No encontré cupos entre {fecha_desde} y una ventana de 14 días.",
        }, ensure_ascii=False)

    sedes = _consultar_catalog_service_cached("/sedes")
    sedes_por_id = {
        str(sede.get("sede_id")): sede
        for sede in (sedes.get("data", []) if sedes.get("ok") else [])
    }
    medicos_por_id: dict[str, dict[str, Any]] = {}
    for opcion in opciones:
        medico_id = str(opcion.get("medico_id", ""))
        if medico_id and medico_id not in medicos_por_id:
            medico = _consultar_catalog_service_cached(f"/medicos/{medico_id}")
            if medico.get("ok") and isinstance(medico.get("data"), dict):
                medicos_por_id[medico_id] = medico["data"]

    opciones_legibles = []
    for opcion in opciones:
        medico = medicos_por_id.get(str(opcion.get("medico_id")), {})
        sede = sedes_por_id.get(str(opcion.get("sede_id")), {})
        nombre_medico = "Médico disponible"
        if medico:
            nombre_medico = f"{medico.get('nombres', '')} {medico.get('apellidos', '')}".strip() or nombre_medico
        opciones_legibles.append({
            **opcion,
            "medico_nombre": nombre_medico,
            "sede_nombre": sede.get("nombre", "Sede disponible"),
            "sede_direccion": sede.get("direccion", ""),
        })

    return json.dumps({
        "ok": True,
        "fecha": resultado["fecha"],
        "opciones": opciones_legibles,
        "mensaje": f"Encontré disponibilidad para el {resultado['fecha']}.",
    }, ensure_ascii=False)


def crear_cita_desde_draft(draft: BookingDraft) -> dict[str, Any]:
    """Crea una cita usando exclusivamente el draft validado por el orquestador."""
    log_event(
        "TOOLS",
        "EXEC",
        "info",
        f"Creando cita desde draft medico={draft.medico_id}, fecha={draft.fecha}, hora={draft.hora_inicio}",
    )
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}
    payload = {
        "usuario_id": draft.usuario_id,
        "medico_id": draft.medico_id,
        "especialidad_id": draft.especialidad_id,
        "tipo_servicio": draft.tipo_servicio,
        "fecha_cita": draft.fecha,
        "hora_inicio": draft.hora_inicio,
        "hora_fin": draft.hora_fin,
        "sede_id": draft.sede_id,
    }
    if draft.descripcion_sintomas:
        payload["descripcion_sintomas"] = draft.descripcion_sintomas
    headers = {"Content-Type": "application/json", "X-User-ID": draft.usuario_id}

    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{citas_url}/citas", json=payload, headers=headers
            )
            if 200 <= response.status_code < 300:
                data = response.json()
                return {"ok": True, "cita_id": str(data.get("cita_id", ""))}
            return {"ok": False, "error": "Problema al agendar la cita."}
    except httpx.TimeoutException:
        existing = _buscar_cita_existente(draft)
        if existing:
            return {"ok": True, "cita_id": existing, "recovered": True}
        return {"ok": False, "timeout": True, "error": "La solicitud tardo demasiado."}
    except httpx.RequestError:
        return {"ok": False, "error": "Problema de conexion."}
    except Exception:
        return {"ok": False, "error": "Error inesperado."}


def _buscar_cita_existente(draft: BookingDraft) -> str | None:
    """Busca una cita programada equivalente después de una respuesta perdida."""
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return None
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{citas_url}/citas/usuario/{draft.usuario_id}",
                headers={"Content-Type": "application/json"},
            )
        if not 200 <= response.status_code < 300:
            return None
        for cita in response.json():
            if (
                cita.get("estado") == "programada"
                and str(cita.get("medico_id")) == draft.medico_id
                and str(cita.get("fecha_cita")) == draft.fecha
                and str(cita.get("hora_inicio", ""))[:5] == draft.hora_inicio[:5]
            ):
                return str(cita.get("cita_id"))
    except (httpx.RequestError, httpx.TimeoutException, ValueError, TypeError):
        return None
    return None


# ---------------------------------------------------------------------------
# Ejecutores normales (PR4, paso 4): funciones puras SIN @tool, invocadas por
# el orquestador solo tras la confirmacion determinista "si". No tocan el
# draft (los fallos dejan el estado para reintentar) y NINGUNA salida contiene
# UUIDs ni el detalle crudo del backend (que puede incluir el cita_id).
# ---------------------------------------------------------------------------


def _detalle_de_error(response: httpx.Response) -> str:
    """Solo el campo `detail` (str) de la respuesta; nunca se usa como salida."""
    try:
        data = response.json()
    except ValueError:
        return ""
    if isinstance(data, dict) and isinstance(data.get("detail"), str):
        return data["detail"]
    return ""


def ejecutar_cancelacion_desde_draft(
    draft: CancelDraft, usuario_id: str
) -> dict[str, Any]:
    """Cancela la cita del draft validado: POST /citas/{cita_id}/cancelar.

    Devuelve {"ok": True}, {"ok": True, "ya_cancelada": True} si la cita ya no
    estaba programada (idempotente), o {"ok": False, "error": ...}. No modifica
    el draft y no expone UUIDs.
    """
    cita_id = str(getattr(draft, "cita_id", "") or "").strip()
    if not cita_id:
        return {"ok": False, "error": "No tengo una cita valida para cancelar."}
    if not usuario_id:
        return {"ok": False, "error": "No hay una identidad autenticada para gestionar tus citas."}

    log_event("TOOLS", "EXEC", "info", "Cancelando cita desde draft")
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}

    payload = {"motivo": draft.motivo or None}
    headers = {"Content-Type": "application/json", "X-User-ID": usuario_id}

    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{citas_url}/citas/{cita_id}/cancelar", json=payload, headers=headers
            )
    except httpx.TimeoutException:
        return {"ok": False, "error": "La solicitud tardo demasiado."}
    except httpx.RequestError:
        return {"ok": False, "error": "Problema de conexion."}
    except Exception:
        return {"ok": False, "error": "Error inesperado."}

    if 200 <= response.status_code < 300:
        return {"ok": True}

    detalle = _detalle_de_error(response)
    if "Solo se puede cancelar una cita en estado 'programada'" in detalle:
        # Ya no estaba programada: cancelar de nuevo es exito idempotente.
        return {"ok": True, "ya_cancelada": True}
    if response.status_code == 404 or "No existe cita" in detalle:
        return {"ok": False, "error": "No encontre esa cita para cancelarla."}
    if response.status_code >= 500:
        return {"ok": False, "error": "El servicio de citas no respondio correctamente."}
    return {"ok": False, "error": "No pude cancelar la cita."}


def ejecutar_reagendamiento_desde_draft(
    draft: RescheduleDraft, usuario_id: str
) -> dict[str, Any]:
    """Reprograma la cita del draft: POST /citas/{cita_id}/reprogramar (atomico).

    Distingue: {"ok": True} | {"ok": False, "cupo_no_disponible": True} |
    {"ok": False, "cita_cambio": True} | {"ok": False, "error": ...} (fallo
    transitorio, sin banderas). No modifica el draft y no expone UUIDs.
    """
    cita_id = str(getattr(draft, "cita_id", "") or "").strip()
    if not cita_id:
        return {"ok": False, "error": "No tengo una cita valida para reprogramar."}
    if not usuario_id:
        return {"ok": False, "error": "No hay una identidad autenticada para gestionar tus citas."}

    log_event("TOOLS", "EXEC", "info", "Reprogramando cita desde draft")
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}

    payload = {
        "nueva_fecha": draft.nueva_fecha,
        "nueva_hora_inicio": draft.nueva_hora_inicio,
        "nueva_hora_fin": draft.nueva_hora_fin,
    }
    headers = {"Content-Type": "application/json", "X-User-ID": usuario_id}

    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{citas_url}/citas/{cita_id}/reprogramar",
                json=payload,
                headers=headers,
            )
    except httpx.TimeoutException:
        return {"ok": False, "error": "La solicitud tardo demasiado."}
    except httpx.RequestError:
        return {"ok": False, "error": "Problema de conexion."}
    except Exception:
        return {"ok": False, "error": "Error inesperado."}

    if 200 <= response.status_code < 300:
        return {"ok": True}

    detalle = _detalle_de_error(response)
    if (
        "ya tiene una cita programada" in detalle
        or "ocupad" in detalle.lower()
        or "no disponible" in detalle.lower()
    ):
        return {
            "ok": False,
            "cupo_no_disponible": True,
            "error": "Ese horario ya esta ocupado; elige otra fecha u hora.",
        }
    if (
        response.status_code == 404
        or "No existe cita" in detalle
        or "Solo se puede reprogramar una cita en estado 'programada'" in detalle
    ):
        return {
            "ok": False,
            "cita_cambio": True,
            "error": "Tu cita cambio o ya no esta programada.",
        }
    if response.status_code >= 500:
        return {"ok": False, "error": "El servicio de citas no respondio correctamente."}
    return {"ok": False, "error": "No pude reprogramar la cita."}


def _normalizar_texto(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).lower().strip()


def _tipo_servicio_desde_especialidad(nombre: str) -> str:
    normalized = _normalizar_texto(nombre)
    if "urgencia" in normalized:
        return "urgencias"
    if "laboratorio" in normalized:
        return "laboratorio"
    if "general" in normalized:
        return "medicina_general"
    return "especialista"


# ---------------------------------------------------------------------------
# Resolucion de citas del usuario por referencia textual (PR4, paso 3).
#
# Regla: NADA de lo que sale hacia el LLM lleva cita_id ni otros UUIDs de
# cita. El cita_id solo se devuelve aqui para uso INTERNO del orquestador
# (drafts); las salidas de aclaracion son solo campos legibles.
# ---------------------------------------------------------------------------

_DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_RANGO_DIAS_REFERENCIA = 14

# Palabras funcionales de peticion (no describen la cita): no cuentan como
# fragmento de busqueda. Los dias/horas/fechas NO usan listas: regex directas.
_STOPWORDS_REFERENCIA = {
    "cancela", "cancelar", "cancele", "cancelame", "cancelada", "cancelado",
    "quiero", "deseo", "puedes", "puede", "favor", "gracias", "hola",
    "cita", "citas", "reprogramar", "reprograma", "reagendar", "reagenda",
    "cambiar", "cambia", "mueve", "mover", "mueveme", "hora", "horario",
    "fecha", "nueva", "nuevo", "otra", "otro", "tengo", "tenemos",
}


def _fecha_legible(fecha_iso: str) -> str:
    """Fecha ISO -> 'lunes 02/11/2026' (dia en espanol, sin depender del LLM)."""
    try:
        parsed = datetime.strptime(str(fecha_iso), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return str(fecha_iso)
    return f"{_DIAS_SEMANA[parsed.weekday()]} {parsed.strftime('%d/%m/%Y')}"


def _parsear_fecha(valor: Any) -> date | None:
    try:
        return datetime.strptime(str(valor), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _obtener_citas_activas(usuario_id: str) -> dict[str, Any]:
    """GET /citas/usuario/{usuario_id} (siempre el VERIFICADO): solo 'programada'."""
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{citas_url}/citas/usuario/{usuario_id}",
                headers={"Content-Type": "application/json"},
            )
    except httpx.TimeoutException:
        return {"ok": False, "error": "La consulta tardo demasiado."}
    except httpx.RequestError:
        return {"ok": False, "error": "Problema de conexion."}
    except Exception:
        return {"ok": False, "error": "Error inesperado."}
    if not 200 <= response.status_code < 300:
        return {"ok": False, "error": "No pude consultar tus citas."}
    try:
        todas = response.json()
    except ValueError:
        return {"ok": False, "error": "Respuesta invalida del servicio de citas."}
    if not isinstance(todas, list):
        # Un 200 con dict de error (u otra cosa) no es una lista de citas.
        return {"ok": False, "error": "Respuesta invalida del servicio de citas."}
    return {
        "ok": True,
        "citas": [c for c in todas if isinstance(c, dict) and c.get("estado") == "programada"],
    }


def _enriquecer_cita(cita: dict[str, Any]) -> dict[str, Any]:
    """Agrega nombres legibles de medico, sede y especialidad (cache TTL existente).

    Si falta algun nombre usa un texto neutro: nunca se expone un UUID como nombre.
    """
    medico_nombre = ""
    sede_nombre = ""
    especialidad_nombre = ""

    medico_id = cita.get("medico_id")
    if medico_id:
        result = _consultar_catalog_service_cached(f"/medicos/{medico_id}")
        if result.get("ok"):
            data = result.get("data") or {}
            medico_nombre = (
                f"{data.get('nombres') or ''} {data.get('apellidos') or ''}".strip()
                or f"{data.get('nombre') or ''} {data.get('apellido') or ''}".strip()
            )

    sede_id = cita.get("sede_id")
    if sede_id:
        result = _consultar_catalog_service_cached("/sedes")
        if result.get("ok"):
            for sede in result.get("data") or []:
                if str(sede.get("sede_id")) == str(sede_id):
                    sede_nombre = str(sede.get("nombre") or "").strip()
                    break

    especialidad_id = cita.get("especialidad_id")
    if especialidad_id:
        result = _consultar_catalog_service_cached("/especialidades")
        if result.get("ok"):
            for especialidad in result.get("data") or []:
                if str(especialidad.get("especialidad_id")) == str(especialidad_id):
                    especialidad_nombre = str(especialidad.get("nombre") or "").strip()
                    break

    return {
        **cita,
        "medico_nombre": medico_nombre or "Médico asignado",
        "sede_nombre": sede_nombre or "Sede",
        "especialidad_nombre": especialidad_nombre or "Consulta médica",
    }


def _extraer_restricciones(referencia: str, hoy: date) -> dict[str, Any]:
    """Extrae restricciones ACUMULATIVAS de lo que dijo el usuario.

    Reglas por regex (sin ampliar listas cerradas: la regex es la regla
    preferida). Cada numero/ palabra reconocido se ENMASCARA del texto para
    que no se cuele como fragmento:

    - horas exactas HH:MM (tambien con am/pm: "10:30 pm" -> "22:30");
    - horas por nivel "10am", "10 pm", "10 de la manana/tarde" (horas_definidas);
    - horas ambiguas "las 10", "a las 7" (sin am/pm): horas_ambiguas, que el
      resolvedor decide contra hora_inicio de 24h;
    - fechas ISO y DD/MM;
    - fechas relativas "hoy", "manana", "pasado manana" (usando `hoy`);
    - dias de semana.
    Los fragmentos restantes (medico/sede/especialidad) son NO bloqueantes:
    se aplican en el resolvedor solo si no vacian el resultado.
    """
    texto = _normalizar_texto(referencia or "")
    restricciones: dict[str, Any] = {
        "dias": set(),
        "fechas": set(),
        "horas": set(),           # exactas "HH:MM"
        "horas_definidas": set(),  # nivel de hora con am/pm o manana/tarde
        "horas_ambiguas": set(),  # "las N" sin am/pm: N se decide despues
        "fragmentos": set(),
    }
    if not texto:
        return restricciones

    def _consumir(patron: str, al_consumir) -> None:
        """Aplica una regex, ejecuta el callback por match y enmascara el match."""

        def _reemplazo(match: re.Match) -> str:
            al_consumir(match)
            return " " * (match.end() - match.start())

        nonlocal texto
        texto = re.sub(patron, _reemplazo, texto)

    # 1) Horas exactas con am/pm: "10:30 pm" -> 22:30.
    def _hora_con_meridiano(match: re.Match) -> None:
        hora = int(match.group(1)) % 12
        if match.group(3).lower() == "pm":
            hora += 12
        restricciones["horas"].add(f"{hora:02d}:{match.group(2)}")

    _consumir(r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", _hora_con_meridiano)

    # 2) Horas exactas HH:MM.
    _consumir(
        r"\b(\d{1,2}):(\d{2})\b",
        lambda m: restricciones["horas"].add(f"{int(m.group(1)):02d}:{m.group(2)}"),
    )

    # 3) "10 de la manana" / "7 de la tarde" (tambien con minutos): nivel de hora.
    def _hora_con_periodo(match: re.Match) -> None:
        hora = int(match.group(1)) % 12
        if match.group(3).lower() == "tarde":
            hora += 12
        restricciones["horas_definidas"].add(hora)

    _consumir(r"\b(\d{1,2})(?::(\d{2}))?\s+de\s+la\s+(manana|tarde)\b", _hora_con_periodo)

    # 4) "10am" / "10 pm": nivel de hora.
    def _hora_meridiano_suelto(match: re.Match) -> None:
        hora = int(match.group(1)) % 12
        if match.group(2).lower() == "pm":
            hora += 12
        restricciones["horas_definidas"].add(hora)

    _consumir(r"\b(\d{1,2})\s*(am|pm)\b", _hora_meridiano_suelto)

    # 5) Fecha ISO.
    def _fecha_iso(match: re.Match) -> None:
        try:
            restricciones["fechas"].add(
                date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            )
        except ValueError:
            pass

    _consumir(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", _fecha_iso)

    # 6) Fecha DD/MM (opcional anio) ANTES de las horas ambiguas: "las 10/11".
    def _fecha_dd_mm(match: re.Match) -> None:
        try:
            if match.group(3):
                anio = int(match.group(3))
                if anio < 100:
                    anio += 2000
            else:
                # Sin anio explicito: primero este anio; si ya paso, el siguiente.
                candidata = date(hoy.year, int(match.group(2)), int(match.group(1)))
                anio = hoy.year if candidata >= hoy else hoy.year + 1
            restricciones["fechas"].add(date(anio, int(match.group(2)), int(match.group(1))))
        except ValueError:
            pass

    _consumir(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", _fecha_dd_mm)

    # 7) Horas ambiguas: "las 10", "a las 7" (sin am/pm). El resolvedor mira
    #    contra hora_inicio con las dos lecturas (7 -> 07:00 y 19:00).
    _consumir(
        r"\b(?:a\s+)?las\s+(\d{1,2})\b",
        lambda m: restricciones["horas_ambiguas"].add(int(m.group(1))),
    )

    # 8) Fechas relativas con `hoy` (antes que la regla de "manana" suelta:
    #    "pasado manana" se consume entero, y "10 de la manana" ya se enmascaro).
    _consumir(
        r"\bpasado\s+manana\b",
        lambda _m: restricciones["fechas"].add(hoy + timedelta(days=2)),
    )
    _consumir(
        r"\bmanana\b",
        lambda _m: restricciones["fechas"].add(hoy + timedelta(days=1)),
    )
    _consumir(r"\bhoy\b", lambda _m: restricciones["fechas"].add(hoy))

    # 9) Dias de semana (sobre el texto ya enmascarado).
    for indice, dia in enumerate(_DIAS_SEMANA):
        if re.search(rf"\b{_normalizar_texto(dia)}\b", texto):
            restricciones["dias"].add(indice)

    for palabra in texto.split():
        if (
            len(palabra) >= 4
            and not palabra.isdigit()
            and ":" not in palabra
            and palabra not in _STOPWORDS_REFERENCIA
            and palabra not in {d for d in (_normalizar_texto(x) for x in _DIAS_SEMANA)}
        ):
            restricciones["fragmentos"].add(palabra)
    return restricciones


def _hora_de_cita(cita: dict[str, Any]) -> int | None:
    """Hora (0-23) de hora_inicio 'HH:MM'; None si no es interpretable."""
    try:
        return int(str(cita.get("hora_inicio") or "")[:2])
    except ValueError:
        return None


def _resolver_horas_ambiguas(
    horas_ambiguas: set[int], candidatas: list[dict[str, Any]]
) -> set[int] | None:
    """Decide horas ambiguas ('las 7' -> 7 u 19) contra hora_inicio (24h).

    - Exactamente UNA lectura coincide con alguna candidata -> se restringe a ella.
    - Las DOS lecturas coinciden -> no se puede decidir: NO se restringe (set()).
    - NINGUNA lectura coincide -> la hora pedida no existe aqui: 0 coincidencias
      (retorna None, que el resolvedor traduce a ninguna candidata).
    """
    resueltas: set[int] = set()
    horas_candidatas = {_hora_de_cita(cita) for cita in candidatas} - {None}
    for ambigua in horas_ambiguas:
        lecturas = {ambigua % 12, (ambigua % 12) + 12}
        coincidentes = lecturas & horas_candidatas
        if len(coincidentes) == 1:
            resueltas |= coincidentes
        elif not coincidentes:
            return None
    return resueltas


def _coincide_con_restricciones(
    cita: dict[str, Any],
    restricciones: dict[str, Any],
    hoy: date,
    *,
    aplicar_fragmentos: bool = False,
    horas_exactas: set[str] | None = None,
    horas_nivel: set[int] | None = None,
) -> bool:
    """True si la cita satisface las restricciones indicadas (todas, AND).

    Los fragmentos solo participan si `aplicar_fragmentos=True` (el resolvedor
    los aplica como filtro NO bloqueante); las horas se pasan ya resueltas
    (exactas "HH:MM" y/o nivel entero 0-23).
    """
    if aplicar_fragmentos and restricciones["fragmentos"]:
        texto_cita = _normalizar_texto(
            f"{cita.get('medico_nombre', '')} {cita.get('sede_nombre', '')} "
            f"{cita.get('especialidad_nombre', '')}"
        )
        if not all(fragmento in texto_cita for fragmento in restricciones["fragmentos"]):
            return False

    if horas_exactas or horas_nivel:
        if horas_exactas and str(cita.get("hora_inicio", ""))[:5] not in horas_exactas:
            return False
        if horas_nivel:
            hora = _hora_de_cita(cita)
            if hora is None or hora not in horas_nivel:
                return False

    requiere_fecha = bool(restricciones["fechas"] or restricciones["dias"])
    fecha_cita = _parsear_fecha(cita.get("fecha_cita"))
    if requiere_fecha and fecha_cita is None:
        return False
    if restricciones["fechas"] and fecha_cita not in restricciones["fechas"]:
        return False
    if restricciones["dias"]:
        # Dia de semana: solo se busca desde 'hoy' inclusive, 14 dias, Bogota.
        if not (hoy <= fecha_cita <= hoy + timedelta(days=_RANGO_DIAS_REFERENCIA - 1)):
            return False
        if fecha_cita.weekday() not in restricciones["dias"]:
            return False
    return True


def _cita_legible(cita: dict[str, Any]) -> dict[str, str]:
    """Representacion de una cita SIN ids: fecha legible, hora, medico y sede."""
    return {
        "fecha": _fecha_legible(cita.get("fecha_cita", "")),
        "hora": str(cita.get("hora_inicio", ""))[:5],
        "medico": str(cita.get("medico_nombre", "")),
        "sede": str(cita.get("sede_nombre", "")),
        "especialidad": str(cita.get("especialidad_nombre", "")),
    }


def _resolver_cita_usuario(
    referencia: str, usuario_id: str | None, hoy: date
) -> dict[str, Any]:
    """Resuelve cual es "la cita que el usuario quiere gestionar".

    Returns:
        {"ok": False, "error": ...} si no hay identidad o fallo de servicio;
        {"ok": True, "encontrada": True, "cita": <cita enriquecida>} con 1
        coincidencia (el cita_id de 'cita' es de uso INTERNO, jamas se envia
        al LLM);
        {"ok": True, "encontrada": False, "candidatas": [<sin ids>], ...} con
        0 o varias coincidencias: sin draft, aclaracion.
    """
    if not usuario_id:
        return {"ok": False, "error": "No hay una identidad autenticada para gestionar tus citas."}

    resultado = _obtener_citas_activas(usuario_id)
    if not resultado.get("ok"):
        return {"ok": False, "error": resultado.get("error") or "No pude consultar tus citas."}

    enriquecidas = [_enriquecer_cita(cita) for cita in resultado["citas"]]
    restricciones = _extraer_restricciones(referencia, hoy)

    # 1) Restricciones de fecha/dia (sin horas ni fragmentos).
    por_fecha = [
        cita
        for cita in enriquecidas
        if _coincide_con_restricciones(cita, restricciones, hoy)
    ]

    # 2) Horas: exactas (HH:MM) + definidas (am/pm) + ambiguas decididas
    #    contra las candidatas por fecha. Si alguna ambigua no coincide con
    #    NINGUNA lectura -> 0 candidatas (None); si ambas coinciden -> sin efecto.
    horas_ambiguas_resueltas = _resolver_horas_ambiguas(
        restricciones["horas_ambiguas"], por_fecha
    )
    if horas_ambiguas_resueltas is None:
        con_horas = []
    else:
        horas_nivel = set(restricciones["horas_definidas"]) | horas_ambiguas_resueltas
        con_horas = [
            cita
            for cita in por_fecha
            if _coincide_con_restricciones(
                cita,
                restricciones,
                hoy,
                horas_exactas=restricciones["horas"],
                horas_nivel=horas_nivel,
            )
        ]

    # 3) Fragmentos NO bloqueantes: si dejan 0 y sin ellos quedan >=1, se
    #    ignoran (nunca vacian el resultado; solo estrechan cuando ayudan).
    coincidentes = con_horas
    if restricciones["fragmentos"] and con_horas:
        con_fragmentos = [
            cita for cita in con_horas if _coincide_con_restricciones(cita, restricciones, hoy, aplicar_fragmentos=True)
        ]
        coincidentes = con_fragmentos or con_horas

    if len(coincidentes) == 1:
        return {"ok": True, "encontrada": True, "cita": coincidentes[0]}
    if not coincidentes:
        return {
            "ok": True,
            "encontrada": False,
            "candidatas": [],
            "mensaje": "No encontre ninguna cita activa que coincida con lo que me indicas.",
        }
    # Varias coincidencias, o referencia sin restricciones con >1 citas activas:
    # nunca elegir la primera; pedir aclaracion con campos legibles y sin ids.
    return {
        "ok": True,
        "encontrada": False,
        "candidatas": [_cita_legible(cita) for cita in coincidentes],
        "mensaje": (
            "Encontre varias citas que podrian ser la que buscas. "
            "Dime la fecha, la hora o el medico para elegir una."
        ),
    }


@tool(context=True)
def proponer_cita(
    fecha: str,
    hora: str,
    sede: str = "",
    elegir_automaticamente: bool = False,
    tool_context: ToolContext | None = None,
) -> str:
    """Selecciona un slot exacto y guarda un draft de reserva sin ejecutarlo."""
    invocation_state = tool_context.invocation_state if tool_context else {}
    turn_context = invocation_state.get("turn_context")
    if turn_context is None or not invocation_state.get("state"):
        return json.dumps({"ok": False, "error": "No hay contexto de conversación para guardar la propuesta."}, ensure_ascii=False)

    state = invocation_state["state"]
    usuario_id = invocation_state.get("usuario_id")
    if not usuario_id or not state.specialty_id:
        return json.dumps({"ok": False, "error": "Falta la identidad del paciente o la especialidad."}, ensure_ascii=False)

    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.get(
                f"{_obtener_citas_service_url()}/citas/slots-detallados",
                params={"especialidad_id": state.specialty_id, "fecha": fecha},
                headers={"Content-Type": "application/json"},
            )
        if not 200 <= response.status_code < 300:
            return json.dumps({"ok": False, "error": "No pude consultar los cupos para esa fecha."}, ensure_ascii=False)
        slots = response.json()
    except (httpx.RequestError, httpx.TimeoutException):
        return json.dumps({"ok": False, "error": "Problema de conexión al consultar los cupos."}, ensure_ascii=False)

    opciones = [
        slot for slot in slots
        if str(slot.get("hora_inicio", ""))[:5] == hora[:5]
    ]
    if sede:
        sede_normalizada = _normalizar_texto(sede)
        sedes_result = _consultar_catalog_service_cached("/sedes")
        sedes = sedes_result.get("data", []) if sedes_result.get("ok") else []
        sede_ids = {
            str(item.get("sede_id"))
            for item in sedes
            if sede_normalizada in _normalizar_texto(str(item.get("nombre", "")))
        }
        opciones = [slot for slot in opciones if str(slot.get("sede_id")) in sede_ids]

    if not opciones:
        return json.dumps({"ok": False, "error": f"No encontré un cupo disponible el {fecha} a las {hora[:5]}."}, ensure_ascii=False)

    sede_ids = {str(slot.get("sede_id")) for slot in opciones}
    if len(sede_ids) > 1 and not elegir_automaticamente:
        return json.dumps({
            "ok": False,
            "requiere_sede": True,
            "opciones": opciones,
            "error": "Hay varias sedes disponibles para esa hora. Indica cuál prefieres.",
        }, ensure_ascii=False)

    sedes_result = _consultar_catalog_service_cached("/sedes")
    sedes = sedes_result.get("data", []) if sedes_result.get("ok") else []
    sedes_por_id = {
        str(item.get("sede_id")): item for item in sedes
    }
    opciones.sort(
        key=lambda slot: (
            _normalizar_texto(
                str(sedes_por_id.get(str(slot.get("sede_id")), {}).get("nombre", ""))
            ),
            str(slot.get("medico_id")),
        )
    )
    seleccion = opciones[0]
    sede_data = next(
        (item for item in sedes if str(item.get("sede_id")) == str(seleccion.get("sede_id"))),
        {},
    )
    medico_result = _consultar_catalog_service_cached(f"/medicos/{seleccion.get('medico_id')}")
    medico_data = medico_result.get("data", {}) if medico_result.get("ok") else {}
    draft = BookingDraft(
        usuario_id=str(usuario_id),
        especialidad_id=str(state.specialty_id),
        especialidad_nombre=state.specialty_name or "Especialidad médica",
        medico_id=str(seleccion["medico_id"]),
        medico_nombre=f"{medico_data.get('nombres', '')} {medico_data.get('apellidos', '')}".strip() or "Médico disponible",
        sede_id=str(seleccion["sede_id"]),
        sede_nombre=str(sede_data.get("nombre", "Sede disponible")),
        sede_direccion=str(sede_data.get("direccion", "")),
        tipo_servicio=_tipo_servicio_desde_especialidad(state.specialty_name or ""),
        fecha=fecha,
        hora_inicio=str(seleccion["hora_inicio"])[:5],
        hora_fin=str(seleccion["hora_fin"])[:5],
        descripcion_sintomas=state.symptoms_summary or "",
    )
    turn_context.set_draft(draft)
    return json.dumps({
        "ok": True,
        "draft_creado": True,
        "fecha": draft.fecha,
        "hora_inicio": draft.hora_inicio,
        "hora_fin": draft.hora_fin,
        "medico_nombre": draft.medico_nombre,
        "sede_nombre": draft.sede_nombre,
        "sede_direccion": draft.sede_direccion,
        "mensaje": "Propuesta guardada. El sistema generará el resumen oficial.",
    }, ensure_ascii=False)


@tool(context=True)
def consultar_citas_usuario(
    usuario_id: str,
    tool_context: ToolContext | None = None,
) -> str:
    """Lista las citas activas (programadas) de un usuario.

    Args:
        usuario_id: UUID del usuario.

    Returns:
        JSON con la lista de citas: cita_id, fecha, hora, medico, especialidad, estado, sede.
    """
    verified_usuario_id = _verified_usuario_id(tool_context)
    if not verified_usuario_id:
        return json.dumps(
            {"ok": False, "error": "No hay una identidad autenticada para consultar tus citas."},
            ensure_ascii=False,
        )
    log_event("TOOLS", "EXEC", "info", "Ejecutando consultar_citas_usuario con identidad verificada")

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}
    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{citas_url}/citas/usuario/{verified_usuario_id}"
            response = client.get(url, headers=headers)
            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                todas = response.json()
                # Filtrar solo citas programadas (activas)
                programadas = [c for c in todas if c.get("estado") == "programada"]
                log_event("TOOLS", "HTTP", "debug", f"Citas usuario {usuario_id} -> {len(programadas)} activas ({elapsed}ms)")
                return json.dumps({
                    "ok": True,
                    "citas": programadas,
                    "total": len(programadas),
                    "mensaje": f"Encontre {len(programadas)} cita(s) activa(s)." if programadas else "No tienes citas activas.",
                }, ensure_ascii=False)
            log_event("TOOLS", "HTTP", "warning", f"Citas usuario {usuario_id} -> {response.status_code} ({elapsed}ms)")
            return json.dumps({"ok": False, "error": "No pude consultar tus citas."}, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La consulta tardo demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexion."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado."}, ensure_ascii=False)


@tool(context=True)
def reagendar_cita(
    usuario_id: str,
    cita_id: str,
    nueva_fecha: str,
    nueva_hora: str,
    tool_context: ToolContext | None = None,
) -> str:
    """Reprograma una cita existente a una nueva fecha y hora.

    Args:
        usuario_id: UUID del usuario (requerido para header X-User-ID).
        cita_id: UUID de la cita a reprogramar.
        nueva_fecha: Nueva fecha en formato YYYY-MM-DD.
        nueva_hora: Nueva hora en formato HH:MM (24h).

    Returns:
        JSON con la confirmación o error.
    """
    verified_usuario_id = _verified_usuario_id(tool_context)
    if not verified_usuario_id:
        return json.dumps(
            {"ok": False, "error": "No hay una identidad autenticada para reprogramar citas."},
            ensure_ascii=False,
        )
    log_event("TOOLS", "EXEC", "info", f"Ejecutando reagendar_cita(cita_id={cita_id}, fecha={nueva_fecha}, hora={nueva_hora})")

    campos_requeridos = {"cita_id": cita_id, "nueva_fecha": nueva_fecha, "nueva_hora": nueva_hora}
    faltantes = [n for n, v in campos_requeridos.items() if not v]
    if faltantes:
        return json.dumps({"ok": False, "error": f"Faltan parametros: {', '.join(faltantes)}."}, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    nueva_hora_fin = _sumar_minutos_a_hora(nueva_hora, 30)
    payload = {
        "nueva_fecha": nueva_fecha,
        "nueva_hora_inicio": nueva_hora,
        "nueva_hora_fin": nueva_hora_fin,
        "motivo": "Reprogramacion por asistente virtual",
    }
    headers = {"Content-Type": "application/json", "X-User-ID": verified_usuario_id}

    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{citas_url}/citas/{cita_id}/reprogramar"
            response = client.post(url, json=payload, headers=headers)
            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                data = response.json()
                log_event("TOOLS", "HTTP", "debug", f"Reprogramar cita {cita_id} -> OK ({elapsed}ms)")
                return json.dumps({
                    "ok": True,
                    "cita_id": str(data.get("cita_id", "")),
                    "nueva_fecha": nueva_fecha,
                    "nueva_hora": nueva_hora,
                    "estado": data.get("estado", "programada"),
                    "mensaje": "Cita reprogramada correctamente!",
                }, ensure_ascii=False)
            error_msg = "No pude reprogramar la cita."
            try:
                detail = response.json().get("detail", "")
                if detail:
                    error_msg = detail
            except Exception:
                pass
            log_event("TOOLS", "HTTP", "warning", f"Reprogramar cita {cita_id} -> {response.status_code} ({elapsed}ms)")
            return json.dumps({"ok": False, "error": error_msg}, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La solicitud tardo demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexion."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado."}, ensure_ascii=False)


@tool(context=True)
def cancelar_cita(
    usuario_id: str,
    cita_id: str,
    motivo: str = "",
    tool_context: ToolContext | None = None,
) -> str:
    """Cancela una cita médica existente.

    Args:
        usuario_id: UUID del usuario (requerido para header X-User-ID).
        cita_id: UUID de la cita a cancelar.
        motivo: Motivo opcional de la cancelación.

    Returns:
        JSON con la confirmación o error.
    """
    verified_usuario_id = _verified_usuario_id(tool_context)
    if not verified_usuario_id:
        return json.dumps(
            {"ok": False, "error": "No hay una identidad autenticada para cancelar citas."},
            ensure_ascii=False,
        )
    log_event("TOOLS", "EXEC", "info", f"Ejecutando cancelar_cita(cita_id={cita_id})")

    if not cita_id:
        return json.dumps({"ok": False, "error": "Necesito el cita_id para cancelar."}, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    payload = {"motivo": motivo or "Cancelacion por asistente virtual"}
    headers = {"Content-Type": "application/json", "X-User-ID": verified_usuario_id}

    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{citas_url}/citas/{cita_id}/cancelar"
            response = client.post(url, json=payload, headers=headers)
            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                log_event("TOOLS", "HTTP", "debug", f"Cancelar cita {cita_id} -> OK ({elapsed}ms)")
                return json.dumps({
                    "ok": True,
                    "cita_id": str(cita_id),
                    "estado": "cancelada",
                    "mensaje": "Cita cancelada correctamente.",
                }, ensure_ascii=False)
            error_msg = "No pude cancelar la cita."
            try:
                detail = response.json().get("detail", "")
                if detail:
                    error_msg = detail
            except Exception:
                pass
            log_event("TOOLS", "HTTP", "warning", f"Cancelar cita {cita_id} -> {response.status_code} ({elapsed}ms)")
            return json.dumps({"ok": False, "error": error_msg}, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La solicitud tardo demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexion."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado."}, ensure_ascii=False)


SCHEDULING_TOOLS = [
    obtener_medicos,
    obtener_sedes,
    obtener_disponibilidad_citas,
    buscar_opciones_cita,
    proponer_cita,
    consultar_citas_usuario,
    reagendar_cita,
    cancelar_cita,
]
