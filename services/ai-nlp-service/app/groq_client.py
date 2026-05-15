from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from .prompts import CLASIFICACION_PROMPT, SYSTEM_PROMPT

GROQ_MODEL = "llama-3.3-70b-versatile"
REQUEST_TIMEOUT_SECONDS = 30.0

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


def configurar_groq() -> None:
	"""Lee GROQ_API_KEY del entorno e inicializa el cliente Groq."""
	global _groq_client

	load_dotenv()
	api_key = os.getenv("GROQ_API_KEY", "").strip()
	if not api_key:
		raise ValueError("Falta GROQ_API_KEY en variables de entorno (.env).")

	_groq_client = Groq(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)


def chat_completion(messages: list[dict], tools: list | None = None) -> tuple[str, dict | None]:
	"""Envia mensajes a Groq y retorna texto de respuesta y tool call (actualmente None)."""
	_ = tools
	client = _asegurar_cliente()

	try:
		response = client.chat.completions.create(
			model=GROQ_MODEL,
			messages=messages,
			max_tokens=400,
		)
	except Exception as exc:
		raise RuntimeError(f"Error al invocar Groq chat completion: {exc}") from exc

	if not response.choices:
		raise RuntimeError("Groq no devolvio choices en la respuesta.")

	content = response.choices[0].message.content or ""
	return content, None


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
	"""Simula ejecucion de tools hasta integrar servicios reales."""
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
		fecha = str(arguments.get("fecha", datetime.utcnow().date().isoformat()))
		hora = str(arguments.get("hora", "09:00"))
		return {
			"ok": True,
			"tool": tool_name,
			"cita_id": f"sim-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
			"fecha": fecha,
			"hora": hora,
			"estado": "confirmada",
			"mensaje": "Cita agendada correctamente (simulacion).",
		}

	return {
		"ok": False,
		"tool": tool_name,
		"error": "Tool no soportada en simulacion.",
	}
