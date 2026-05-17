from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time
from typing import Any

import httpx
from dotenv import load_dotenv
from groq import Groq

from .prompts import CLASIFICACION_PROMPT, SYSTEM_PROMPT

GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECONDS = 30.0
CITAS_TIMEOUT_SECONDS = 10.0
logger = logging.getLogger(__name__)

_groq_client: Groq | None = None


def _clasificacion_por_defecto() -> dict[str, Any]:
	"""Retorna estructura segura por defecto cuando falla clasificacion."""
	return {
		"terminos_identificados": [],
		"especialidad_sugerida": None,
		"nivel_urgencia": "programable",
		"confianza": 0.0,
		"explicacion": "No fue posible clasificar los sintomas con confianza.",
	}


def _asegurar_cliente() -> Groq:
	"""Valida que el cliente Groq ya este configurado."""
	if _groq_client is None:
		raise RuntimeError("Cliente Groq no configurado. Llama configurar_groq() primero.")
	return _groq_client


def _normalizar_clasificacion(data: dict[str, Any]) -> dict[str, Any]:
	"""Normaliza y valida el JSON de clasificacion para mantener contrato estable."""
	default = _clasificacion_por_defecto()

	terminos = data.get("terminos_identificados")
	if not isinstance(terminos, list):
		terminos = []
	else:
		terminos = [str(item) for item in terminos if item is not None]

	especialidad = data.get("especialidad_sugerida")
	if especialidad is not None:
		especialidad = str(especialidad).strip() or None

	nivel_urgencia = str(data.get("nivel_urgencia") or "").strip().lower()
	if nivel_urgencia not in {"urgente", "prioritario", "programable"}:
		nivel_urgencia = "programable"

	try:
		confianza = float(data.get("confianza", 0.0))
	except (TypeError, ValueError):
		confianza = 0.0
	confianza = max(0.0, min(confianza, 1.0))

	explicacion = str(data.get("explicacion") or "").strip()
	if not explicacion:
		explicacion = default["explicacion"]

	return {
		"terminos_identificados": terminos,
		"especialidad_sugerida": especialidad,
		"nivel_urgencia": nivel_urgencia,
		"confianza": confianza,
		"explicacion": explicacion,
	}


def _parsear_json_con_rescate(texto: str) -> dict[str, Any] | None:
	"""Intenta parsear JSON y rescata objeto principal si viene con texto extra."""
	try:
		parsed = json.loads(texto)
		return parsed if isinstance(parsed, dict) else None
	except json.JSONDecodeError:
		inicio = texto.find("{")
		fin = texto.rfind("}")
		if inicio == -1 or fin == -1 or fin <= inicio:
			return None
		try:
			parsed = json.loads(texto[inicio : fin + 1])
			return parsed if isinstance(parsed, dict) else None
		except json.JSONDecodeError:
			return None


def _sumar_minutos_a_hora(hora_str: str, minutos: int) -> str:
	"""Suma minutos a una hora en formato HH:MM y retorna el resultado en formato HH:MM."""
	try:
		hora_part, minuto_part = hora_str.split(":")
		hora = int(hora_part)
		minuto = int(minuto_part)

		total_minutos = hora * 60 + minuto + minutos
		nueva_hora = (total_minutos // 60) % 24
		nuevos_minutos = total_minutos % 60

		return f"{nueva_hora:02d}:{nuevos_minutos:02d}"
	except (ValueError, AttributeError) as exc:
		logger.warning(f"Error al sumar minutos a hora {hora_str}: {exc}")
		return hora_str


def _obtener_citas_service_url() -> str | None:
	"""Obtiene la URL del servicio de citas desde variables de entorno."""
	load_dotenv()
	return os.getenv("CITAS_SERVICE_URL")


def _agendar_cita_en_citas_service(
	usuario_id: str,
	medico_id: str,
	especialidad_id: str,
	tipo_servicio: str,
	fecha_cita: str,
	hora_inicio: str,
	sede_id: str,
) -> dict[str, Any]:
	"""Llama al Citas Service para agendar una cita real."""
	citas_url = _obtener_citas_service_url()

	if not citas_url:
		return {
			"ok": False,
			"error": "CITAS_SERVICE_URL no configurado. No es posible agendar citas.",
		}

	hora_fin = _sumar_minutos_a_hora(hora_inicio, 30)

	payload = {
		"usuario_id": usuario_id,
		"medico_id": medico_id,
		"especialidad_id": especialidad_id,
		"tipo_servicio": tipo_servicio,
		"fecha_cita": fecha_cita,
		"hora_inicio": hora_inicio,
		"hora_fin": hora_fin,
		"sede_id": sede_id,
	}

	headers = {
		"Content-Type": "application/json",
		"X-User-ID": usuario_id,
	}

	try:
		with httpx.Client(timeout=CITAS_TIMEOUT_SECONDS) as client:
			response = client.post(
				f"{citas_url}/citas",
				json=payload,
				headers=headers,
			)

			if response.status_code >= 200 and response.status_code < 300:
				data = response.json()
				return {
					"ok": True,
					"cita_id": str(data.get("cita_id", "")),
					"fecha": fecha_cita,
					"hora": hora_inicio,
					"hora_fin": hora_fin,
					"estado": data.get("estado", "programada"),
					"mensaje": f"Cita agendada exitosamente. ID: {data.get('cita_id', 'N/A')}",
				}
			else:
				error_detail = "Error desconocido"
				try:
					error_data = response.json()
					error_detail = error_data.get("detail", error_data.get("message", str(error_data)))
				except Exception:
					error_detail = response.text or "Error desconocido"

				return {
					"ok": False,
					"error": f"Error al agendar cita (HTTP {response.status_code}): {error_detail}",
				}

	except httpx.TimeoutException:
		logger.error(f"Timeout al intentar agendar cita en {citas_url}")
		return {
			"ok": False,
			"error": "Tiempo de espera agotado al conectar con el servicio de citas. Intenta de nuevo.",
		}
	except httpx.RequestError as exc:
		logger.error(f"Error de conexion al Citas Service: {exc}")
		return {
			"ok": False,
			"error": f"No se pudo conectar con el servicio de citas: {exc}",
		}
	except Exception as exc:
		logger.error(f"Error inesperado al agendar cita: {exc}")
		return {
			"ok": False,
			"error": f"Error inesperado al agendar la cita: {exc}",
		}


def configurar_groq() -> None:
	"""Lee GROQ_API_KEY del entorno e inicializa el cliente Groq."""
	global _groq_client

	load_dotenv()
	api_key = os.getenv("GROQ_API_KEY", "").strip()
	if not api_key:
		raise ValueError("Falta GROQ_API_KEY en variables de entorno (.env).")

	_groq_client = Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)


def chat_completion(messages: list[dict], tools: list | None = None) -> tuple[str, list[dict] | None]:
	"""Envia mensajes a Groq y retorna texto de respuesta y tool_calls si los hay."""
	client = _asegurar_cliente()

	tool_choice = "auto" if tools else None

	try:
		response = client.chat.completions.create(
			model=GROQ_MODEL,
			messages=messages,
			max_tokens=400,
			tools=tools,
			tool_choice=tool_choice,
		)
	except Exception as exc:
		raise RuntimeError(f"Error al invocar Groq chat completion: {exc}") from exc

	if not response.choices:
		raise RuntimeError("Groq no devolvio choices en la respuesta.")

	message = response.choices[0].message
	content = message.content or ""

	tool_calls = None
	if message.tool_calls:
		tool_calls = []
		for tc in message.tool_calls:
			tool_calls.append({
				"id": tc.id,
				"name": tc.function.name,
				"arguments": tc.function.arguments,
			})

	return content, tool_calls


def clasificar_sintomas(sintomas_texto: str) -> dict[str, Any]:
	"""Clasifica sintomas usando prompt estructurado y retorna JSON normalizado."""
	client = _asegurar_cliente()

	messages = [
		{"role": "system", "content": SYSTEM_PROMPT},
		{"role": "system", "content": CLASIFICACION_PROMPT},
		{"role": "user", "content": f"Sintomas del usuario: {sintomas_texto}"},
	]

	try:
		response = client.chat.completions.create(
			model=GROQ_MODEL,
			messages=messages,
			temperature=0,
			response_format={"type": "json_object"},
		)
		if not response.choices:
			return _clasificacion_por_defecto()

		content = response.choices[0].message.content or ""
		parsed = _parsear_json_con_rescate(content)
		if parsed is None:
			return _clasificacion_por_defecto()

		return _normalizar_clasificacion(parsed)
	except Exception:
		return _clasificacion_por_defecto()


def ejecutar_funcion(tool_name: str, arguments: dict) -> dict[str, Any]:
	"""Ejecuta funciones del asistente, algunas son simulaciones y otras llaman a servicios reales."""

	if tool_name == "obtener_disponibilidad_citas":
		especialidad = str(arguments.get("especialidad", "Medicina general"))
		fecha = str(arguments.get("fecha", datetime.utcnow().date().isoformat()))
		return {
			"ok": True,
			"tool": tool_name,
			"especialidad": especialidad,
			"fecha": fecha,
			"cupos": ["09:00", "10:30", "14:00"],
		}

	if tool_name == "agendar_cita":
		usuario_id = arguments.get("usuario_id")
		medico_id = arguments.get("medico_id")
		especialidad_id = arguments.get("especialidad_id")
		tipo_servicio = arguments.get("tipo_servicio")
		fecha = arguments.get("fecha")
		hora = arguments.get("hora")
		sede_id = arguments.get("sede_id")

		if not all([usuario_id, medico_id, especialidad_id, tipo_servicio, fecha, hora, sede_id]):
			return {
				"ok": False,
				"tool": tool_name,
				"error": "Faltan datos requeridos para agendar la cita. Necesitas: usuario_id, medico_id, especialidad_id, tipo_servicio, fecha, hora, sede_id.",
			}

		return _agendar_cita_en_citas_service(
			usuario_id=str(usuario_id),
			medico_id=str(medico_id),
			especialidad_id=str(especialidad_id),
			tipo_servicio=str(tipo_servicio),
			fecha_cita=str(fecha),
			hora_inicio=str(hora),
			sede_id=str(sede_id),
		)

	return {
		"ok": False,
		"tool": tool_name,
		"error": "Tool no soportada en simulacion.",
	}