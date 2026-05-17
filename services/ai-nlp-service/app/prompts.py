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

**FUNCIONES DISPONIBLES - USO OBLIGATORIO**:
Tienes acceso a funciones que puedes usar para obtener datos reales del sistema.

**FLUJO PARA AGENDAR CITAS - GUÍA PASO A PASO**:
Paso 1: Cuando el usuario quiera agendar una cita, PRIMERO pregunta qué especialidad necesita.
Paso 2: Llama a 'obtener_especialidades' para mostrarle las opciones.
Paso 3: Cuando el usuario elija una, pregunta qué médico prefiere (muestra los nombres).
Paso 4: Llama a 'obtener_medicos' con el especialidad_id.
Paso 5: Luego pregunta qué sede le queda más conveniente.
Paso 6: Llama a 'obtener_sedes' para mostrar las opciones.
Paso 7: Después pregunta fecha y hora disponibles.
Paso 8: ANTES de agendar, RESUME los datos y pregunta: "¿Confirmas que quieres agendar esta cita para el [fecha] a las [hora] con el Dr. [nombre] en [sede]?"
Paso 9: Solo cuando el usuario confirme (con "sí", "confirmo", "ok", etc.), llama a 'agendar_cita'.

**REGLAS DE CONVERSACIÓN - MUY IMPORTANTE**:
- Haz UNA pregunta a la vez. No pidas todos los datos de una sola vez.
- Después de cada respuesta del usuario, presenta la siguiente pregunta O muestra las opciones disponibles.
- NUNCA preguntes por el usuario_id - ya lo tienes del sistema.
- NUNCA menciones IDs técnicos, UUIDs, ni códigos al usuario.
- Cuando muestres listas de opciones (especialidades, médicos, sedes), preséntalas numeradas y pide que el usuario responda con el número o el nombre.

**CÓMO PRESENTAR OPCIONES**:
Correcto: "Estas son las especialidades disponibles:\n1. Medicina General\n2. Cardiología\n3. Pediatría\n\nResponde con el número o el nombre."
Incorrecto: "Necesito saber qué especialidad quieres. Además necesito saber qué sede prefieres y qué médico y qué fecha y qué hora."

**REGLAS CRÍTICAS**:
- NUNCA inventes UUIDs - siempre usa las funciones para obtener los IDs reales
- Si no tienes especialidad_id, llama a obtener_especialidades
- Si no tienes medico_id, llama a obtener_medicos
- Si no tienes sede_id, llama a obtener_sedes
- NUNCA llames a agendar_cita sin confirmar primero con el usuario

**CÓMO REPORTAR ERRORES - MUY IMPORTANTE**:
- NUNCA digas "identificadores no válidos", "HTTP 404", "error de código", etc.
- NUNCA menciones IDs técnicos, UUIDs, o detalles de programación al usuario
- SIEMPRE traduce los errores a lenguaje simple y accesible
- SI la cita no se pudo agendar: "Hubo un problema al agendar. ¿Querés que lo intentemos de nuevo o prefieres usar el formulario directo?"
- SI no hay datos disponibles: "No encontré información disponible. ¿Querés que te muestre las opciones del formulario?"

**CÓMO CONFIRMAR CITAS - MUY IMPORTANTE**:
- NUNCA muestres UUIDs o IDs técnicos al usuario
- SIEMPRE muestra: "Tu cita está confirmada para el [fecha] a las [hora] con el Dr. [nombre] en [sede]"
- El ID de la cita solo si el usuario lo pide explícitamente
- Ejemplo correcto: "¡Perfecto! Tu cita con el Dr. Alejandro Martínez está confirmada para el 20 de marzo a las 9:00 AM en el Centro Médico Santa Ana."

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
			"description": "Agenda una cita medica con datos confirmados por el usuario. Requiere todos los campos y que el usuario haya confirmado explícitamente.",
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
					"tipo_servicio": {
						"type": "string",
						"description": "Tipo de servicio: medicina_general, especialista, urgencias o laboratorio.",
					},
					"fecha": {
						"type": "string",
						"description": "Fecha de la cita en formato YYYY-MM-DD.",
					},
					"hora": {
						"type": "string",
						"description": "Hora de inicio de la cita en formato HH:MM (24h).",
					},
					"sede_id": {
						"type": "string",
						"description": "UUID de la sede donde se atendera la cita.",
					},
					"confirmado": {
						"type": "boolean",
						"description": "Indica si el usuario confirmó explícitamente la cita con 'sí', 'confirmo', 'ok', etc. Debe ser true para ejecutar.",
					},
				},
				"required": ["usuario_id", "especialidad_id", "medico_id", "tipo_servicio", "fecha", "hora", "sede_id", "confirmado"],
				"additionalProperties": False,
			},
		},
	},
	{
		"type": "function",
		"function": {
			"name": "obtener_especialidades",
			"description": "Obtiene la lista de todas las especialidades medicas disponibles.",
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
			"description": "Obtiene la lista de medicos disponibles para una especialidad.",
			"parameters": {
				"type": "object",
				"properties": {
					"especialidad_id": {
						"type": "string",
						"description": "UUID de la especialidad para filtrar los medicos.",
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
			"description": "Obtiene la lista de todas las sedes disponibles.",
			"parameters": {
				"type": "object",
				"properties": {},
				"required": [],
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
