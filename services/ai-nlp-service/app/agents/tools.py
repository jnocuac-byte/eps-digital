from __future__ import annotations

import json
import os
import time
import unicodedata
from datetime import datetime
from threading import RLock
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv
from strands import tool
from strands.types.tools import ToolContext

from ..core.logger import log_event
from ..core.conversation_state import BookingDraft

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


@tool
def consultar_citas_usuario(usuario_id: str) -> str:
    """Lista las citas activas (programadas) de un usuario.

    Args:
        usuario_id: UUID del usuario.

    Returns:
        JSON con la lista de citas: cita_id, fecha, hora, medico, especialidad, estado, sede.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando consultar_citas_usuario(usuario_id={usuario_id})")

    if not usuario_id:
        return json.dumps({"ok": False, "error": "Necesito el usuario_id para buscar sus citas."}, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    headers = {"Content-Type": "application/json"}
    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{citas_url}/citas/usuario/{usuario_id}"
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


@tool
def reagendar_cita(usuario_id: str, cita_id: str, nueva_fecha: str, nueva_hora: str) -> str:
    """Reprograma una cita existente a una nueva fecha y hora.

    Args:
        usuario_id: UUID del usuario (requerido para header X-User-ID).
        cita_id: UUID de la cita a reprogramar.
        nueva_fecha: Nueva fecha en formato YYYY-MM-DD.
        nueva_hora: Nueva hora en formato HH:MM (24h).

    Returns:
        JSON con la confirmación o error.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando reagendar_cita(cita_id={cita_id}, fecha={nueva_fecha}, hora={nueva_hora})")

    campos_requeridos = {"usuario_id": usuario_id, "cita_id": cita_id, "nueva_fecha": nueva_fecha, "nueva_hora": nueva_hora}
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
    headers = {"Content-Type": "application/json", "X-User-ID": str(usuario_id)}

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


@tool
def cancelar_cita(usuario_id: str, cita_id: str, motivo: str = "") -> str:
    """Cancela una cita médica existente.

    Args:
        usuario_id: UUID del usuario (requerido para header X-User-ID).
        cita_id: UUID de la cita a cancelar.
        motivo: Motivo opcional de la cancelación.

    Returns:
        JSON con la confirmación o error.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando cancelar_cita(cita_id={cita_id})")

    if not usuario_id or not cita_id:
        return json.dumps({"ok": False, "error": "Necesito usuario_id y cita_id para cancelar."}, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    payload = {"motivo": motivo or "Cancelacion por asistente virtual"}
    headers = {"Content-Type": "application/json", "X-User-ID": str(usuario_id)}

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
