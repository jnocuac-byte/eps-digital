from __future__ import annotations

from typing import Any

# Modelo recomendado para este servicio.
MODEL_NAME = "gpt-4o-mini"


SYSTEM_PROMPT = """
Eres un asistente virtual medico de una EPS en Colombia.

Reglas principales:
- No diagnosticas ni formulas tratamientos definitivos; solo orientas y apoyas el triaje.
- Clasifica la urgencia en uno de estos niveles:
  - urgente: vida en riesgo o signos de alarma mayores; requiere atencion inmediata.
  - prioritario: requiere atencion en menos de 48 horas.
  - programable: puede manejarse con cita regular.
- Sugiere la especialidad medica mas adecuada segun los sintomas descritos.
- Responde siempre en espanol, con lenguaje claro, empatico y accionable.
- Si identificas posible riesgo vital, indica ir a urgencias de inmediato o llamar a emergencias.

IMPORTANTE - Formato y longitud:
- **Responde en formato Markdown** para mejor lectura.
- Usa **negritas** para palabras clave.
- Usa **saltos de linea** entre ideas.
- Mantén tus respuestas CLARAS y DIRECTAS. Responde en un máximo de 600 caracteres.
- MAXIMO 2-3 oraciones para respuestas simples.
- MAXIMO 150 palabras para respuestas con consejos.
- No escribas listas extensas ni parrafos largos.
- Si necesitas mas detalles, pregunta al usuario que desea saber.

Buenas practicas de respuesta:
- Haz preguntas de aclaracion cuando falte contexto clinico importante.
- Resume en bullets cortos cuando ayude a la comprension.
- Evita tecnicismos innecesarios.
- Mantente dentro del rol de orientacion para EPS en Colombia.

Especialidades habilitadas:
- Medicina General
- Cardiología
- Pediatría
- Odontología
- Neurología
- Ginecología
- Oftalmología

Reglas:
- Solo puedes sugerir especialidades habilitadas.
- Si no hay suficiente claridad clínica, sugiere Medicina General.
""".strip()


CLASIFICACION_PROMPT = """
Analiza los sintomas del usuario y devuelve SOLO un JSON valido con esta estructura exacta:
{
  "terminos_identificados": ["lista", "de", "terminos", "medicos"],
  "especialidad_sugerida": "nombre de especialidad",
  "nivel_urgencia": "urgente|prioritario|programable",
  "confianza": 0.95,
  "explicacion": "breve explicacion"
}

Reglas:
- terminos_identificados: arreglo de strings, puede ir vacio si no hay terminos claros.
- especialidad_sugerida: string o null si no se puede inferir con confianza.
- nivel_urgencia: debe ser exactamente urgente, prioritario o programable.
- confianza: numero entre 0.0 y 1.0.
- explicacion: maximo 2 lineas, clara y basada en los sintomas.
- No incluyas markdown, texto extra, ni bloques de codigo.
- Si hay signos de alarma evidentes, nivel_urgencia debe ser "urgente".
- especialidad_sugerida debe ser una de las especialidades habilitadas.
- Si no hay suficiente información, usa Medicina General.
""".strip()


# Definicion de funciones para OpenAI function calling.
ASSISTANT_TOOLS: list[dict[str, Any]] = [
	{
		"type": "function",
		"function": {
			"name": "obtener_disponibilidad_citas",
			"description": "Consulta disponibilidad de citas por especialidad y fecha.",
			"parameters": {
				"type": "object",
				"properties": {
					"especialidad": {
						"type": "string",
						"description": "Nombre de la especialidad medica, por ejemplo medicina interna.",
					},
					"fecha": {
						"type": "string",
						"description": "Fecha deseada en formato ISO YYYY-MM-DD.",
					},
				},
				"required": ["especialidad", "fecha"],
				"additionalProperties": False,
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "agendar_cita",
			"description": "Agenda una cita medica con datos confirmados por el usuario.",
			"parameters": {
				"type": "object",
				"properties": {
					"usuario_id": {
						"type": "string",
						"description": "UUID del usuario en el sistema.",
					},
					"especialidad_id": {
						"type": "string",
						"description": "UUID de la especialidad seleccionada.",
					},
					"medico_id": {
						"type": "string",
						"description": "UUID del medico seleccionado.",
					},
					"fecha": {
						"type": "string",
						"description": "Fecha de la cita en formato ISO YYYY-MM-DD.",
					},
					"hora": {
						"type": "string",
						"description": "Hora de la cita en formato HH:MM (24h).",
					},
				},
				"required": ["usuario_id", "especialidad_id", "medico_id", "fecha", "hora"],
				"additionalProperties": False,
			},
		},
	},
]


def build_system_message() -> dict[str, str]:
	"""Construye el mensaje de sistema para el asistente principal."""
	return {"role": "system", "content": SYSTEM_PROMPT}


def build_user_message(user_text: str) -> dict[str, str]:
	"""Construye un mensaje de usuario para el chat."""
	return {"role": "user", "content": user_text}


def build_assistant_message(text: str) -> dict[str, str]:
	"""Construye un mensaje de asistente para historial local."""
	return {"role": "assistant", "content": text}


def build_chat_messages(user_text: str, history: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
	"""Arma la lista de mensajes para conversacion general con contexto previo."""
	messages: list[dict[str, str]] = [build_system_message()]
	if history:
		messages.extend(history)
	messages.append(build_user_message(user_text))
	return messages


def build_clasificacion_messages(sintomas_texto: str) -> list[dict[str, str]]:
	"""Arma mensajes para forzar clasificacion estructurada de sintomas."""
	return [
		build_system_message(),
		{"role": "system", "content": CLASIFICACION_PROMPT},
		{
			"role": "user",
			"content": f"Sintomas del usuario: {sintomas_texto}",
		},
	]


def get_assistant_tools() -> list[dict[str, Any]]:
	"""Retorna las tools configuradas para function calling."""
	return ASSISTANT_TOOLS
