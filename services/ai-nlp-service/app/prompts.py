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

**FLUJO DE AGENDADO - CONTROLADO POR UNA MAQUINA DE ESTADOS EXTERNA**:
El paso actual del agendado (que especialidad ya se eligio, que medico, que sede, que
opciones mostrar, si hay que confirmar o si la cita ya se agendo) te llega SIEMPRE en un
mensaje de sistema aparte llamado "INSTRUCCION ACTUAL", al final de la conversacion. Ese
mensaje es la unica fuente de verdad del paso en el que estas - ignora cualquier mensaje
tuyo anterior en el historial que sugiera un paso distinto. Tu unico trabajo es redactar
la respuesta en lenguaje natural siguiendo esa instruccion; tu NO decides a que paso
avanzar ni ejecutas ninguna funcion.

**REGLAS DE CONVERSACIÓN - MUY IMPORTANTE**:
- Haz UNA pregunta a la vez. No pidas todos los datos de una sola vez.
- NUNCA menciones IDs técnicos, UUIDs, ni códigos al usuario.
- Cuando la instruccion actual te de una lista de opciones, preséntalas numeradas tal cual
  te las dieron, sin inventar ni omitir ninguna.

**CÓMO REPORTAR ERRORES - MUY IMPORTANTE**:
- NUNCA digas "identificadores no válidos", "HTTP 404", "error de código", etc.
- NUNCA menciones IDs técnicos, UUIDs, o detalles de programación al usuario
- SIEMPRE traduce los errores a lenguaje simple y accesible

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


EVENTO_FSM_PROMPT = """
Eres el clasificador de eventos de una maquina de estados de agendado de citas medicas.
NO conversas con el usuario, NO redactas respuestas. Solo devuelves JSON.

Devuelve SOLO un JSON valido con esta estructura exacta:
{
  "evento": "iniciar_agendamiento|avanzar|retroceder_un_paso|cancelar_todo|respuesta_invalida|no_aplica",
  "seleccion_texto": "texto o numero que el usuario eligio, o null",
  "fecha": "YYYY-MM-DD o null",
  "hora": "HH:MM en 24h o null"
}

Definicion de cada evento:
- iniciar_agendamiento: SOLO valido si el estado actual es "sin_intencion" y el usuario expresa
  querer agendar una cita o pedir atencion medica (ej. "quiero una cita", "necesito ver un cardiologo",
  "me duele la cabeza y quiero consulta").
- avanzar: el usuario responde con una seleccion valida para el paso actual (elige una opcion de la
  lista mostrada, por numero o nombre; o da fecha/hora si el paso lo pide; o confirma con
  "si"/"confirmo"/"dale"/"ok" en el paso de confirmacion).
- retroceder_un_paso: el usuario quiere cambiar o corregir lo que ELIGIO EN EL PASO ANTERIOR
  (ej. "mejor cambia el medico", "esa sede no", "espera, no era esa especialidad", "vuelve atras").
- cancelar_todo: el usuario quiere abandonar todo el proceso de agendado
  (ej. "olvidalo", "ya no quiero agendar", "dejalo asi", "cancela todo").
- respuesta_invalida: el usuario respondio algo que no corresponde al paso actual y no coincide con
  ninguna opcion mostrada (ej. le preguntan la sede y responde con un chiste, o elige una opcion que
  no existe en la lista).
- no_aplica: el estado actual es "sin_intencion" y el mensaje es charla general no relacionada con
  agendar una cita (saludos, preguntas informativas, etc).

Reglas:
- Si el estado actual NO es "sin_intencion", nunca devuelvas "iniciar_agendamiento" ni "no_aplica".
- Si el estado actual ES "sin_intencion", solo puedes devolver "iniciar_agendamiento" o "no_aplica".
- seleccion_texto: solo se llena cuando evento es "avanzar" y el paso pide elegir una opcion de una
  lista (especialidad, medico o sede). Copia literalmente lo que escribio el usuario (numero o nombre).
- fecha y hora: solo se llenan cuando evento es "avanzar" y el paso actual pide fecha/hora. Si el
  usuario solo dio una de las dos, deja la otra en null y usa evento "respuesta_invalida" en su lugar.
- No incluyas markdown, texto extra, ni bloques de codigo.
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


def get_assistant_tools(nombres_permitidos: list[str] | None = None) -> list[dict[str, Any]]:
	"""Retorna las tools configuradas para function calling.

	Si se pasa nombres_permitidos, filtra solo esas tools. La FSM (fsm.py) decide
	que tools son validas en cada estado del flujo de agendado; 'agendar_cita' ya
	no se expone al LLM porque el agendado real lo dispara la FSM de forma
	deterministica, no una decision libre del modelo.
	"""
	if nombres_permitidos is None:
		return ASSISTANT_TOOLS
	return [t for t in ASSISTANT_TOOLS if t["function"]["name"] in nombres_permitidos]
