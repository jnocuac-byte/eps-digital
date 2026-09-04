from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv
from strands import tool

from ..core.logger import log_event

CITAS_TIMEOUT_SECONDS = 4.0


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
    result = _consultar_catalog_service("/especialidades")
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

    result = _consultar_catalog_service(f"/especialidades/{especialidad_id}/medicos")
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
    result = _consultar_catalog_service("/sedes")
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
def agendar_cita(
    usuario_id: str,
    especialidad_id: str,
    medico_id: str,
    tipo_servicio: str,
    fecha: str,
    hora: str,
    sede_id: str,
) -> str:
    """Agenda una cita médica con los datos confirmados por el usuario.

    Args:
        usuario_id: UUID del usuario autenticado.
        especialidad_id: UUID de la especialidad médica (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
        medico_id: UUID del médico seleccionado (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).
        tipo_servicio: Tipo de servicio. Opciones: medicina_general, especialista, urgencias, laboratorio.
        fecha: Fecha de la cita en formato YYYY-MM-DD (ej: 2026-09-07).
        hora: Hora de la cita en formato HH:MM en 24 horas (ej: 08:00, 14:30).
        sede_id: UUID de la sede/clínica (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx).

    Returns:
        JSON con la confirmación: cita_id (UUID), fecha, hora, estado, mensaje.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando agendar_cita(medico_id={medico_id}, fecha={fecha}, hora={hora})")

    if not all([usuario_id, medico_id, especialidad_id, tipo_servicio, fecha, hora, sede_id]):
        return json.dumps({
            "ok": False,
            "tool": "agendar_cita",
            "error": "Faltan datos para agendar la cita. Necesito: usuario_id, especialidad_id, medico_id, tipo_servicio, fecha, hora, sede_id.",
        }, ensure_ascii=False)

    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return json.dumps({"ok": False, "error": "CITAS_SERVICE_URL no configurado."}, ensure_ascii=False)

    hora_fin = _sumar_minutos_a_hora(hora, 30)
    payload = {
        "usuario_id": usuario_id,
        "medico_id": medico_id,
        "especialidad_id": especialidad_id,
        "tipo_servicio": tipo_servicio,
        "fecha_cita": fecha,
        "hora_inicio": hora,
        "hora_fin": hora_fin,
        "sede_id": sede_id,
    }
    headers = {"Content-Type": "application/json", "X-User-ID": str(usuario_id)}

    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            response = client.post(
                f"{citas_url}/citas", json=payload, headers=headers
            )
            if 200 <= response.status_code < 300:
                data = response.json()
                return json.dumps({
                    "ok": True,
                    "cita_id": str(data.get("cita_id", "")),
                    "fecha": fecha,
                    "hora": hora,
                    "estado": data.get("estado", "programada"),
                    "mensaje": "Cita agendada correctamente!",
                }, ensure_ascii=False)
            return json.dumps({
                "ok": False,
                "error": "Problema al agendar. Intentamos de nuevo?",
            }, ensure_ascii=False)
    except httpx.TimeoutException:
        return json.dumps({"ok": False, "error": "La solicitud tardo demasiado."}, ensure_ascii=False)
    except httpx.RequestError:
        return json.dumps({"ok": False, "error": "Problema de conexion."}, ensure_ascii=False)
    except Exception:
        return json.dumps({"ok": False, "error": "Error inesperado."}, ensure_ascii=False)


SCHEDULING_TOOLS = [
    obtener_especialidades,
    obtener_medicos,
    obtener_sedes,
    obtener_disponibilidad_citas,
    agendar_cita,
]
