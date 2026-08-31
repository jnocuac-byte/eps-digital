from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from .conversation_state import ConversationState, classify_intent
from .llm_provider import LLMProviderFactory, AllProvidersFailedError
from .logger import log_event

MAX_HISTORY_MESSAGES = 6
MAX_TOOL_ITERATIONS = 5

_HANDOFF_SIGNALS = [
    "puedo ayudarle a agendar",
    "le recomiendo agendar una cita",
    "proceder con el agendamiento",
    "buscar disponibilidad",
    "solicitar una cita",
    "reservar una cita",
    "agendar su cita",
    "continuar con el agendamiento",
]

_TOOL_CALL_PATTERN = re.compile(
    r'\{\s*"tool_call"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"[^}]*\}\s*\}'
)

_TOOL_NAME_PATTERN = re.compile(r'"name"\s*:\s*"([^"]+)"')
_TOOL_PARAMS_PATTERN = re.compile(r'"params"\s*:\s*(\{[^}]*\})')

_RESPUESTA_BLOCK_PATTERN = re.compile(
    r"\[RESPUESTA\]\n(.*?)(?=\n\[CLASIFICACION\]|\Z)", re.DOTALL
)
_CLASIFICACION_BLOCK_PATTERN = re.compile(
    r"\[CLASIFICACION\]\s*\n(\{.*\})", re.DOTALL
)

_RESPUESTA_VACIA_FALLBACK = (
    "Entiendo tu consulta. Un asistente te podrá ayudar con más detalle. "
    "¿Podrías darme más información sobre lo que necesitas?"
)


def _extraer_tool_call(texto: str) -> dict[str, Any] | None:
    """Extrae un tool_call del texto de respuesta del LLM.

    Busca el patrón: {"tool_call": {"name": "...", "params": {...}}}
    Retorna {"name": "...", "params": {...}} o None si no hay tool call.
    """
    match = _TOOL_CALL_PATTERN.search(texto)
    if not match:
        return None

    try:
        name_match = _TOOL_NAME_PATTERN.search(texto[match.start() : match.end()])
        params_match = _TOOL_PARAMS_PATTERN.search(texto[match.start() : match.end()])

        if not name_match:
            return None

        name = name_match.group(1)
        params_str = params_match.group(1) if params_match else "{}"

        # Normalizar comillas simples a dobles para JSON
        params_str = params_str.replace("'", '"')
        params = json.loads(params_str)

        return {"name": name, "params": params}
    except (json.JSONDecodeError, AttributeError):
        return None


def _detectar_handoff(respuesta: str) -> bool:
    """Detecta si el agente sugiere un handoff al siguiente agente."""
    respuesta_lower = respuesta.lower()
    return any(s in respuesta_lower for s in _HANDOFF_SIGNALS)


def _extraer_respuesta_bloque(texto: str) -> str:
    """Extrae el contenido del bloque [RESPUESTA] del texto del LLM.

    Algoritmo de 3 capas:
    1. Busca bloque [RESPUESTA] con regex → retorna si no está vacío
    2. Si [RESPUESTA] está vacío, busca texto antes de [CLASIFICACION]
    3. Si todo está vacío, retorna fallback contextualizado
    """
    # Capa 1: bloque [RESPUESTA] explícito
    match = _RESPUESTA_BLOCK_PATTERN.search(texto)
    if match:
        contenido = match.group(1).strip()
        if contenido:
            log_event("ORCH", "EXTRACT", "debug", f"[RESPUESTA] extraído ({len(contenido)} chars)")
            return contenido
        log_event("ORCH", "EXTRACT", "warning", "Bloque [RESPUESTA] encontrado pero vacío")

    # Capa 2: texto antes de [CLASIFICACION] (excluyendo la propia etiqueta)
    if "[CLASIFICACION]" in texto:
        partes = texto.split("[CLASIFICACION]", 1)
        contenido = partes[0].strip()
        # Limpiar prefijos como [RESPUESTA] sueltos
        contenido = re.sub(r"^\[RESPUESTA\]\s*\n?", "", contenido).strip()
        if contenido:
            log_event("ORCH", "EXTRACT", "debug", f"Texto antes de [CLASIFICACION] extraído ({len(contenido)} chars)")
            return contenido
    else:
        # Sin bloque [CLASIFICACION], el texto completo es la respuesta (legacy)
        contenido = texto.strip()
        if contenido:
            log_event("ORCH", "EXTRACT", "debug", f"Texto legacy extraído ({len(contenido)} chars)")
            return contenido

    log_event("ORCH", "EXTRACT", "warning", "Respuesta vacía, aplicando fallback")
    return _RESPUESTA_VACIA_FALLBACK


def _extraer_clasificacion_bloque(texto: str) -> dict | None:
    """Extrae y parsea el JSON del bloque [CLASIFICACION] del texto del LLM.

    Intenta en orden:
    1. Buscar bloque [CLASIFICACION] con regex
    2. Buscar JSON embebido entre llaves (fallback legacy)
    3. Retornar None si no se pudo parsear
    """
    # Intento 1: bloque [CLASIFICACION] explícito
    match = _CLASIFICACION_BLOCK_PATTERN.search(texto)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and "nivel_urgencia" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    # Intento 2: JSON embebido entre llaves (fallback para respuestas legacy)
    try:
        parsed = json.loads(texto)
        if isinstance(parsed, dict) and "nivel_urgencia" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio != -1 and fin > inicio:
        try:
            parsed = json.loads(texto[inicio : fin + 1])
            if isinstance(parsed, dict) and "nivel_urgencia" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    return None


class Orchestrator:
    """Máquina de estados que enruta conversaciones entre TriageAgent y SchedulingAgent."""

    def __init__(self, factory: LLMProviderFactory):
        self._factory = factory
        self._states: dict[str, ConversationState] = {}

        # Carga lazy de prompts (evita circular imports)
        self._triage_prompt: str | None = None
        self._scheduling_prompt: str | None = None

    def _get_triage_prompt(self) -> str:
        if self._triage_prompt is None:
            from ..agents.triage.prompt import TRIAGE_SYSTEM_PROMPT
            self._triage_prompt = TRIAGE_SYSTEM_PROMPT
        return self._triage_prompt

    def _get_scheduling_prompt(self) -> str:
        if self._scheduling_prompt is None:
            from ..agents.scheduling.prompt import SCHEDULING_SYSTEM_PROMPT
            self._scheduling_prompt = SCHEDULING_SYSTEM_PROMPT
        return self._scheduling_prompt

    def get_state(
        self, conversation_id: str, db: Session | None = None
    ) -> ConversationState:
        """Recupera el estado de una conversación o crea uno nuevo.

        Si db se provee y el state no está en memoria, intenta rehidratar
        desde la columna estado_orquestador de la BD.
        """
        if conversation_id not in self._states:
            # Intentar rehidratar desde la BD
            if db is not None:
                from ..crud import cargar_estado_orquestador

                estado_json = cargar_estado_orquestador(db, conversation_id)
                if estado_json:
                    try:
                        data = json.loads(estado_json)
                        self._states[conversation_id] = ConversationState.from_dict(data)
                        log_event(
                            "ORCH", "STATE_LOAD", "info",
                            f"Estado rehidratado para conversación {conversation_id}"
                        )
                        return self._states[conversation_id]
                    except (json.JSONDecodeError, KeyError) as exc:
                        log_event(
                            "ORCH", "STATE_LOAD", "warning",
                            f"Error rehidratando estado: {exc}. Usando estado vacío."
                        )

            self._states[conversation_id] = ConversationState()
        return self._states[conversation_id]

    def _persist_state(
        self, conversation_id: str, state: ConversationState, db: Session
    ) -> None:
        """Guarda el estado del orquestador en la BD."""
        from ..crud import guardar_estado_orquestador

        try:
            estado_json = json.dumps(state.to_dict(), ensure_ascii=False)
            guardar_estado_orquestador(db, conversation_id, estado_json)
        except Exception as exc:
            log_event(
                "ORCH", "STATE_SAVE", "warning",
                f"Error persistiendo estado para {conversation_id}: {exc}"
            )

    def _build_system_prompt(self, state: ConversationState) -> str:
        """Construye el system prompt según el agente activo, inyectando el contexto."""
        if state.active_agent == "scheduling":
            base = self._get_scheduling_prompt()
        else:
            base = self._get_triage_prompt()

        contexto = state.to_system_context()
        return f"{base}\n\n## CONTEXTO DE LA CONVERSACIÓN\n{contexto}"

    def _build_llm_messages(
        self,
        history: list[dict[str, str]],
        user_message: str,
        state: ConversationState,
        usuario_id: str | None = None,
    ) -> list[dict[str, str]]:
        """Construye la lista de mensajes para el LLM con sliding window."""
        # System prompt
        system_prompt = self._build_system_prompt(state)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Inyectar usuario_id si está disponible
        if usuario_id:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        f"El usuario actual está autenticado. "
                        f"Su ID es: {usuario_id}. "
                        f"Usa este ID cuando llames a funciones que requieran usuario_id."
                    ),
                }
            )

        # Sliding window: últimos N mensajes del historial
        window = history[-MAX_HISTORY_MESSAGES:]
        messages.extend(window)

        # Mensaje actual del usuario
        messages.append({"role": "user", "content": user_message})

        return messages

    async def _tool_loop(
        self,
        messages: list[dict[str, str]],
        state: ConversationState,
    ) -> str:
        """Ejecuta el loop de function calling.

        1. Envía messages al LLM.
        2. Si la respuesta contiene un tool_call, ejecuta la tool.
        3. Alimenta el resultado de vuelta al LLM.
        4. Repite hasta que no haya más tool calls o se alcance el máximo.
        """
        from ..agents.tools import ejecutar_funcion

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response_text, provider_name = self._factory.complete(
                    messages=messages,
                    max_tokens=1500,
                )
                log_event(
                    "ORCH", "TOOL_LOOP", "info",
                    f"Iteración {iteration + 1}, provider={provider_name}, "
                    f"response_len={len(response_text)}"
                )
            except AllProvidersFailedError as exc:
                log_event("ORCH", "TOOL_LOOP", "error", f"Todos los proveedores fallaron: {exc}")
                return (
                    "Lo siento, estoy teniendo dificultades técnicas en este momento. "
                    "Por favor, intenta de nuevo en unos minutos."
                )

            # Buscar tool call en la respuesta
            tool_call = _extraer_tool_call(response_text)
            if not tool_call:
                # No hay tool call: extraer bloque [RESPUESTA] si existe
                return _extraer_respuesta_bloque(response_text)

            tool_name = tool_call["name"]
            tool_params = tool_call["params"]
            log_event(
                "ORCH", "TOOL_LOOP", "info",
                f"Tool call detectado: {tool_name}({tool_params})"
            )

            # Ejecutar la tool
            try:
                result = ejecutar_funcion(tool_name, tool_params)
            except Exception as exc:
                log_event("ORCH", "TOOL_LOOP", "error", f"Error ejecutando {tool_name}: {exc}")
                result = {"ok": False, "error": f"Error interno ejecutando {tool_name}"}

            # Alimentar resultado al LLM para que genere respuesta en lenguaje natural
            result_str = json.dumps(result, ensure_ascii=False)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"[Resultado de la herramienta '{tool_name}']: {result_str}\n\n"
                        f"Ahora responde al usuario en lenguaje natural con base en este resultado. "
                        f"Si necesitas más datos del sistema para continuar el flujo de agendamiento "
                        f"(ej: médicos, sedes, disponibilidad), puedes realizar otro tool_call. "
                        f"Si ya tienes toda la información necesaria, entrega la respuesta final al usuario."
                    ),
                }
            )

            # Actualizar estado con resultados relevantes
            self._actualizar_estado_desde_tool(state, tool_name, result)

        # Si llegamos aquí, el LLM siguió pidiendo tools después del máximo
        log_event("ORCH", "TOOL_LOOP", "warning", "Máximo de iteraciones alcanzado en tool loop")
        return response_text

    def _actualizar_estado_desde_tool(
        self, state: ConversationState, tool_name: str, result: dict
    ) -> None:
        """Actualiza el ConversationState con información obtenida de las tools."""
        if not result.get("ok"):
            return

        if tool_name == "obtener_especialidades":
            especialidades = result.get("especialidades", [])
            if especialidades and len(especialidades) == 1:
                esp = especialidades[0]
                state.specialty_id = str(esp.get("especialidad_id", ""))
                state.specialty_name = esp.get("nombre", "")

        elif tool_name == "obtener_medicos":
            medicos = result.get("medicos", [])
            if medicos and len(medicos) == 1:
                med = medicos[0]
                state.selected_doctor_id = str(med.get("medico_id", ""))
                state.selected_doctor_name = (
                    f"{med.get('nombre', '')} {med.get('apellido', '')}".strip()
                )

        elif tool_name == "obtener_sedes":
            sedes = result.get("sedes", [])
            if sedes and len(sedes) == 1:
                sede = sedes[0]
                state.selected_sede_id = str(sede.get("sede_id", ""))
                state.selected_sede_name = sede.get("nombre", "")

        elif tool_name == "agendar_cita":
            state.pending_confirmation = False
            log_event(
                "ORCH", "STATE", "info",
                f"Cita agendada: {result.get('cita_id', 'N/A')}"
            )

    async def process(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, str]],
        usuario_id: str | None = None,
        db: Session | None = None,
    ) -> tuple[str, ConversationState]:
        """Punto de entrada principal del orquestador.

        Args:
            conversation_id: ID de la conversación (para recuperar/crear estado).
            message: Mensaje actual del usuario.
            history: Historial de mensajes [{role, content}, ...].
            usuario_id: ID del usuario autenticado (opcional).
            db: Sesión de SQLAlchemy para persistencia del state (opcional).

        Returns:
            Tupla (respuesta_texto, estado_actualizado).
        """
        state = self.get_state(conversation_id, db=db)
        state.message_count += 1

        log_event(
            "ORCH", "INTENT", "debug",
            f"Conv={conversation_id[:8]}.. msg#{state.message_count} "
            f"agent_actual={state.active_agent}"
        )

        # 1. Clasificar intención y posible cambio de agente
        intent = classify_intent(message, state)
        previous_agent = state.active_agent

        log_event(
            "ORCH", "INTENT", "info",
            f"Intención clasificada: {intent} (agente anterior: {previous_agent})"
        )

        if intent == "triage":
            state.active_agent = "triage"
        elif intent == "scheduling":
            # Enviar contexto del triaje al scheduling en handoff
            if previous_agent == "triage" and state.specialty_id:
                state.handoff_context = {
                    "specialty_id": state.specialty_id,
                    "specialty_name": state.specialty_name,
                    "symptoms_summary": state.symptoms_summary,
                    "urgency_level": state.urgency_level,
                }
            state.active_agent = "scheduling"

        # 2. Construir mensajes para el LLM
        llm_messages = self._build_llm_messages(history, message, state, usuario_id)

        # 3. Ejecutar el agente con tool loop
        response_text = await self._tool_loop(llm_messages, state)

        # 4. Detectar handoff automático (triage → scheduling)
        if state.active_agent == "triage" and _detectar_handoff(response_text):
            state.active_agent = "scheduling"
            state.handoff_context = {
                "specialty_id": state.specialty_id,
                "specialty_name": state.specialty_name,
                "symptoms_summary": state.symptoms_summary,
                "urgency_level": state.urgency_level,
            }
            log_event(
                "ORCH", "HANDOFF", "info",
                f"Handoff detectado: triage → scheduling (specialty={state.specialty_name})"
            )

        # 5. Extraer clasificación del triage si hay JSON en la respuesta
        if state.active_agent == "triage":
            clasificacion = _extraer_clasificacion_bloque(response_text)
            if clasificacion:
                state.specialty_id = clasificacion.get("especialidad_sugerida_id")
                state.specialty_name = clasificacion.get("especialidad_sugerida_nombre")
                state.symptoms_summary = clasificacion.get("resumen_clinico")
                state.urgency_level = clasificacion.get("nivel_urgencia")
                state.red_flag_detected = (
                    clasificacion.get("red_flag", {}).get("detected", False)
                )

        # 6. Persistir estado en la BD si hay sesión disponible
        if db is not None:
            self._persist_state(conversation_id, state, db)

        return response_text, state
