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
    descripcion_sintomas: str = "",
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
        descripcion_sintomas: Descripción opcional de los síntomas reportados por el paciente.

    Returns:
        JSON con la confirmación: cita_id (UUID), fecha, hora, estado, mensaje.
    """
    log_event("TOOLS", "EXEC", "info", f"Ejecutando agendar_cita(medico_id={medico_id}, fecha={fecha}, hora={hora})")

    campos_requeridos = {
        "usuario_id": usuario_id,
        "medico_id": medico_id,
        "especialidad_id": especialidad_id,
        "tipo_servicio": tipo_servicio,
        "fecha": fecha,
        "hora": hora,
        "sede_id": sede_id,
    }
    faltantes = [nombre for nombre, valor in campos_requeridos.items() if not valor]
    if faltantes:
        return json.dumps({
            "ok": False,
            "tool": "agendar_cita",
            "error": f"Faltan parametros requeridos para agendar la cita: {', '.join(faltantes)}. Solicitalos al usuario o al contexto antes de intentar de nuevo.",
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
    if descripcion_sintomas:
        payload["descripcion_sintomas"] = descripcion_sintomas
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
    obtener_especialidades,
    obtener_medicos,
    obtener_sedes,
    obtener_disponibilidad_citas,
    agendar_cita,
    consultar_citas_usuario,
    reagendar_cita,
    cancelar_cita,
]
