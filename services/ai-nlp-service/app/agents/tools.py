from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

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
                log_event("TOOLS", "HTTP", "debug", f"Catalog {endpoint} → {response.status_code} ({elapsed}ms)")
                return {"ok": True, "data": response.json()}
            log_event("TOOLS", "HTTP", "warning", f"Catalog {endpoint} → {response.status_code} ({elapsed}ms)")
            return {"ok": False, "error": "No pude obtener la información."}
    except httpx.TimeoutException:
        log_event("TOOLS", "TIMEOUT", "warning", f"Catalog {endpoint} timeout ({CITAS_TIMEOUT_SECONDS}s)")
        return {"ok": False, "error": "La consulta tardó demasiado."}
    except httpx.RequestError as exc:
        log_event("TOOLS", "ERROR", "error", f"Catalog {endpoint} conexión: {exc}")
        return {"ok": False, "error": "Problema de conexión."}
    except Exception as exc:
        log_event("TOOLS", "ERROR", "error", f"Catalog {endpoint} error: {exc}")
        return {"ok": False, "error": "Error inesperado."}


def _consultar_citas_service(
    endpoint: str, params: dict | None = None
) -> dict[str, Any]:
    """Consulta al Appointments Service y retorna los datos."""
    citas_url = _obtener_citas_service_url()
    if not citas_url:
        return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}

    headers = {"Content-Type": "application/json"}
    log_event("TOOLS", "HTTP", "debug", f"Citas GET {endpoint} params={params}")
    t0 = time.time()
    try:
        with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
            url = f"{citas_url}{endpoint}"
            if params:
                response = client.get(url, params=params, headers=headers)
            else:
                response = client.get(url, headers=headers)

            elapsed = round((time.time() - t0) * 1000)
            if 200 <= response.status_code < 300:
                log_event("TOOLS", "HTTP", "debug", f"Citas {endpoint} → {response.status_code} ({elapsed}ms)")
                return {"ok": True, "data": response.json()}
            log_event("TOOLS", "HTTP", "warning", f"Citas {endpoint} → {response.status_code} ({elapsed}ms)")
            return {"ok": False, "error": "No pude obtener la información."}
    except httpx.TimeoutException:
        log_event("TOOLS", "TIMEOUT", "warning", f"Citas {endpoint} timeout ({CITAS_TIMEOUT_SECONDS}s)")
        return {"ok": False, "error": "La consulta tardó demasiado."}
    except httpx.RequestError as exc:
        log_event("TOOLS", "ERROR", "error", f"Citas {endpoint} conexión: {exc}")
        return {"ok": False, "error": "Problema de conexión."}
    except Exception as exc:
        log_event("TOOLS", "ERROR", "error", f"Citas {endpoint} error: {exc}")
        return {"ok": False, "error": "Error inesperado."}


def _sumar_minutos_a_hora(hora_str: str, minutos: int) -> str:
    try:
        parts = hora_str.split(":")
        total = int(parts[0]) * 60 + int(parts[1]) + minutos
        return f"{(total // 60) % 24:02d}:{total % 60:02d}"
    except (ValueError, AttributeError):
        return hora_str


ASSISTANT_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "obtener_disponibilidad_citas",
            "description": "Consulta horarios disponibles para una especialidad en una fecha específica. Retorna los slots de tiempo libres.",
            "parameters": {
                "type": "object",
                "properties": {
                    "especialidad_id": {
                        "type": "string",
                        "description": "UUID de la especialidad médica.",
                    },
                    "fecha": {
                        "type": "string",
                        "description": "Fecha en formato YYYY-MM-DD.",
                    },
                },
                "required": ["especialidad_id", "fecha"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "agendar_cita",
            "description": "Agenda una cita médica con datos confirmados por el usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "usuario_id": {"type": "string", "description": "UUID del usuario."},
                    "especialidad_id": {
                        "type": "string",
                        "description": "UUID de la especialidad.",
                    },
                    "medico_id": {"type": "string", "description": "UUID del médico."},
                    "tipo_servicio": {
                        "type": "string",
                        "description": "Tipo: medicina_general, especialista, urgencias, laboratorio.",
                    },
                    "fecha": {"type": "string", "description": "Fecha YYYY-MM-DD."},
                    "hora": {
                        "type": "string",
                        "description": "Hora HH:MM (24h).",
                    },
                    "sede_id": {"type": "string", "description": "UUID de la sede."},
                    "confirmado": {
                        "type": "boolean",
                        "description": "Confirmación explícita del usuario.",
                    },
                },
                "required": [
                    "usuario_id",
                    "especialidad_id",
                    "medico_id",
                    "tipo_servicio",
                    "fecha",
                    "hora",
                    "sede_id",
                    "confirmado",
                ],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_especialidades",
            "description": "Lista de especialidades médicas disponibles.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_medicos",
            "description": "Lista de médicos para una especialidad.",
            "parameters": {
                "type": "object",
                "properties": {
                    "especialidad_id": {
                        "type": "string",
                        "description": "UUID de la especialidad.",
                    },
                },
                "required": ["especialidad_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_sedes",
            "description": "Lista de sedes disponibles.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        },
    },
]


def ejecutar_funcion(tool_name: str, arguments: dict) -> dict[str, Any]:
    """Ejecuta una tool del asistente, retornando el resultado como dict."""
    log_event("TOOLS", "EXEC", "info", f"Ejecutando tool '{tool_name}' args={arguments}")

    if tool_name == "obtener_disponibilidad_citas":
        especialidad_id = arguments.get("especialidad_id")
        fecha = arguments.get("fecha")

        if not especialidad_id or not fecha:
            return {
                "ok": False,
                "error": "Necesito la especialidad y la fecha para buscar horarios.",
            }

        result = _consultar_citas_service(
            "/citas/slots-disponibles",
            params={"especialidad_id": especialidad_id, "fecha": fecha},
        )
        if result.get("ok"):
            slots_raw = result.get("data", [])
            cupos = [slot.get("hora_inicio", "") for slot in slots_raw if slot.get("hora_inicio")]
            return {
                "ok": True,
                "tool": tool_name,
                "especialidad_id": especialidad_id,
                "fecha": fecha,
                "cupos": cupos,
                "slots_completos": slots_raw,
                "mensaje": (
                    f"Encontré {len(cupos)} horarios disponibles para el {fecha}."
                    if cupos
                    else f"No hay horarios disponibles para el {fecha}."
                ),
            }
        return {
            "ok": False,
            "error": result.get("error", "No pude consultar la disponibilidad."),
        }

    if tool_name == "obtener_especialidades":
        result = _consultar_catalog_service("/especialidades")
        if result.get("ok"):
            return {
                "ok": True,
                "especialidades": result.get("data", []),
                "mensaje": "Estas son las especialidades disponibles.",
            }
        return result

    if tool_name == "obtener_medicos":
        eid = arguments.get("especialidad_id")
        if not eid:
            return {
                "ok": False,
                "error": "Necesito qué especialidad querés.",
            }
        result = _consultar_catalog_service(f"/especialidades/{eid}/medicos")
        if result.get("ok"):
            return {
                "ok": True,
                "medicos": result.get("data", []),
                "mensaje": "Aquí están los médicos disponibles.",
            }
        return result

    if tool_name == "obtener_sedes":
        result = _consultar_catalog_service("/sedes")
        if result.get("ok"):
            return {
                "ok": True,
                "sedes": result.get("data", []),
                "mensaje": "Estas son las sedes disponibles.",
            }
        return result

    if tool_name == "agendar_cita":
        usuario_id = arguments.get("usuario_id")
        medico_id = arguments.get("medico_id")
        especialidad_id = arguments.get("especialidad_id")
        tipo_servicio = arguments.get("tipo_servicio")
        fecha = arguments.get("fecha")
        hora = arguments.get("hora")
        sede_id = arguments.get("sede_id")
        confirmado = arguments.get("confirmado", False)

        if not confirmado:
            return {
                "ok": False,
                "tool": tool_name,
                "error": "Necesito que confirmes los datos antes de agendar.",
            }
        if not all(
            [usuario_id, medico_id, especialidad_id, tipo_servicio, fecha, hora, sede_id]
        ):
            return {
                "ok": False,
                "tool": tool_name,
                "error": "Faltan datos para agendar la cita.",
            }

        citas_url = _obtener_citas_service_url()
        if not citas_url:
            return {"ok": False, "error": "CITAS_SERVICE_URL no configurado."}

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
                    return {
                        "ok": True,
                        "cita_id": str(data.get("cita_id", "")),
                        "fecha": fecha,
                        "hora": hora,
                        "estado": data.get("estado", "programada"),
                        "mensaje": "¡Cita agendada correctamente!",
                    }
                return {
                    "ok": False,
                    "error": "Problema al agendar. ¿Intentamos de nuevo?",
                }
        except httpx.TimeoutException:
            return {"ok": False, "error": "La solicitud tardó demasiado."}
        except httpx.RequestError:
            return {"ok": False, "error": "Problema de conexión."}
        except Exception:
            return {"ok": False, "error": "Error inesperado."}

    return {"ok": False, "tool": tool_name, "error": "Tool no soportada."}
