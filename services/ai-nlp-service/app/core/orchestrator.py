from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session
from strands import Agent

from .conversation_state import ConversationState, classify_intent, es_uuid_valido
from .logger import log_event

MAX_HISTORY_MESSAGES = 6

_ROUTING_KEY_PREFIX = "strands:model_routing"


def _extraer_provider_usado(invocation_state: dict) -> str:
    """Extrae el nombre del proveedor LLM seleccionado por el ModelRouter.

    Lee el _RoutingState almacenado en invocation_state bajo la key
    ``strands:model_routing:<agent_hex>:<router_hex>`` y retorna
    ``state.candidate.name`` (ej: "mistral", "gemini").
    """
    for key, value in invocation_state.items():
        if key.startswith(_ROUTING_KEY_PREFIX):
            candidate = getattr(value, "candidate", None)
            if candidate is not None:
                return getattr(candidate, "name", "unknown")
    return "unknown"


def _extraer_explicacion(response: Any) -> str | None:
    """Extrae explicacion_al_paciente de cualquier formato de respuesta del LLM.

    Maneja 3 casos:
      1. Objeto Pydantic con .output (structured output exitoso)
      2. response cuyo str() contiene JSON crudo
      3. Fallback (no se pudo extraer)

    Returns:
        Texto de explicación al paciente o None si no se pudo extraer.
    """
    # Caso 1: Objeto Pydantic con .output (structured output)
    if hasattr(response, "output") and response.output is not None:
        output = response.output
        if isinstance(output, dict):
            return output.get("explicacion_al_paciente")
        return getattr(output, "explicacion_al_paciente", None)

    # Caso 2: response como string que contiene JSON crudo
    raw = str(response)
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return data.get("explicacion_al_paciente")
        except (json.JSONDecodeError, TypeError):
            pass

    return None


def _extraer_clasificacion(response: Any) -> dict | Any | None:
    """Extrae el objeto de clasificación de cualquier formato de respuesta.

    Retorna el objeto Pydantic/dict original para extraer campos adicionales
    (resumen_clinico, especialidad, etc.).
    """
    if hasattr(response, "output") and response.output is not None:
        return response.output

    raw = str(response)
    stripped = raw.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError):
            pass

    return None


class Orchestrator:
    """Orquestador multi-agente basado en Strands Agents.

    Reemplaza el _tool_loop manual con el motor de ejecución nativo de Strands.
    Cada agente (triage, scheduling) es un Strands Agent que ejecuta tools
    de forma autónoma cuando el LLM lo requiere.
    """

    def __init__(self, triage_agent: Agent, scheduling_agent: Agent):
        self._triage_agent = triage_agent
        self._scheduling_agent = scheduling_agent
        self._states: dict[str, ConversationState] = {}

    def get_state(
        self, conversation_id: str, db: Session | None = None
    ) -> ConversationState:
        """Recupera el estado de una conversación o crea uno nuevo."""
        if conversation_id not in self._states:
            if db is not None:
                from ..crud import cargar_estado_orquestador

                estado_json = cargar_estado_orquestador(db, conversation_id)
                if estado_json:
                    try:
                        data = json.loads(estado_json)
                        self._states[conversation_id] = ConversationState.from_dict(data)
                        log_event(
                            "ORCH", "STATE_LOAD", "info",
                            f"Estado rehidratado para conversacion {conversation_id[:8]}"
                        )
                        return self._states[conversation_id]
                    except (json.JSONDecodeError, KeyError) as exc:
                        log_event(
                            "ORCH", "STATE_LOAD", "warning",
                            f"Error rehidratando estado: {exc}. Usando estado vacio."
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
                f"Error persistiendo estado para {conversation_id[:8]}: {exc}"
            )

    def _build_system_context(self, state: ConversationState) -> str:
        """Construye contexto inyectable en el system prompt del agente."""
        parts: list[str] = []
        if state.specialty_name:
            parts.append(f"Especialidad identificada: {state.specialty_name}")
        if state.specialty_id:
            parts.append(f"specialty_id: {state.specialty_id}")
        if state.symptoms_summary:
            parts.append(f"Sintomas reportados: {state.symptoms_summary}")
        if state.urgency_level:
            parts.append(f"Nivel de urgencia: {state.urgency_level}")
        if state.selected_doctor_name:
            parts.append(f"Medico seleccionado: {state.selected_doctor_name}")
        if state.selected_doctor_id:
            parts.append(f"medico_id: {state.selected_doctor_id}")
        if state.selected_sede_name:
            parts.append(f"Sede seleccionada: {state.selected_sede_name}")
        if state.selected_sede_id:
            parts.append(f"sede_id: {state.selected_sede_id}")
        return "\n".join(parts) if parts else ""

    async def _process_triage(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, str]],
        usuario_id: str | None,
        state: ConversationState,
    ) -> str:
        """Procesa un mensaje con el agente de triaje.

        El agente retorna TriageAnalysis estructurado directamente.
        """
        state.active_agent = "triage"

        # Construir mensaje con historial
        full_message = message
        if history:
            history_text = "\n".join(
                f"{'Paciente' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in history[-MAX_HISTORY_MESSAGES:]
            )
            full_message = f"Historial de la conversacion:\n{history_text}\n\nMensaje actual del paciente: {message}"

        log_event("ORCH", "TRIAGE", "info", f"Invocando triage_agent conv={conversation_id[:8]}")

        try:
            self._triage_agent.messages = []
            invocation_state: dict = {}
            response = self._triage_agent(full_message, invocation_state=invocation_state)
            provider = _extraer_provider_usado(invocation_state)

            # Extraer clasificación (Pydantic, dict o JSON crudo)
            classification = _extraer_clasificacion(response)

            if classification is not None:
                # Extraer campos de la clasificación (soporta Pydantic y dict)
                if isinstance(classification, dict):
                    esp_id = classification.get("especialidad_sugerida_id")
                    esp_nombre = classification.get("especialidad_sugerida_nombre")
                    resumen = classification.get("resumen_clinico")
                    urgencia = classification.get("nivel_urgencia")
                    red_flag = classification.get("red_flag", {})
                    red_flag_detected = red_flag.get("detected", False) if isinstance(red_flag, dict) else False
                else:
                    esp_id = getattr(classification, "especialidad_sugerida_id", None)
                    esp_nombre = getattr(classification, "especialidad_sugerida_nombre", None)
                    resumen = getattr(classification, "resumen_clinico", None)
                    urgencia = getattr(classification, "nivel_urgencia", None)
                    rf = getattr(classification, "red_flag", None)
                    red_flag_detected = getattr(rf, "detected", False) if rf else False

                log_event(
                    "ORCH", "TRIAGE", "info",
                    f"Clasificacion: especialidad={esp_nombre}, urgencia={urgencia} "
                    f"provider={provider}"
                )

                # Actualizar estado (incluir symptoms_summary explícitamente)
                state.specialty_id = esp_id
                state.specialty_name = esp_nombre
                state.symptoms_summary = resumen
                state.urgency_level = urgencia
                state.red_flag_detected = red_flag_detected

                # Detectar handoff automático → scheduling
                if urgencia in ("programable", "prioritario"):
                    state.active_agent = "scheduling"
                    state.handoff_context = {
                        "specialty_id": state.specialty_id,
                        "specialty_name": state.specialty_name,
                        "symptoms_summary": state.symptoms_summary,
                        "urgency_level": state.urgency_level,
                    }
                    log_event(
                        "ORCH", "HANDOFF", "info",
                        f"Handoff auto: triage → scheduling (specialty={state.specialty_name})"
                    )

            # Extraer respuesta en lenguaje natural (nunca JSON crudo)
            respuesta = _extraer_explicacion(response)
            if not respuesta:
                respuesta = (
                    f"Segun el analisis, se sugiere {state.specialty_name or 'una especialidad'} "
                    f"con nivel de urgencia {state.urgency_level or 'a determinar'}. "
                    "Un asistente te ayudara a agendar tu cita."
                )

            return respuesta

        except Exception as exc:
            log_event("ORCH", "TRIAGE", "error", f"Error en triage_agent: {exc}")
            return (
                "Lo siento, estoy teniendo dificultades tecnicas. "
                "Por favor, intenta de nuevo en unos minutos."
            )

    async def _process_scheduling(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, str]],
        usuario_id: str | None,
        state: ConversationState,
    ) -> str:
        """Procesa un mensaje con el agente de agendamiento.

        Strands ejecuta las tools (obtener_medicos, agendar_cita, etc.)
        de forma autónoma en un loop interno.
        """
        state.active_agent = "scheduling"

        # Construir contexto del paciente para el agente
        context_parts: list[str] = []
        if usuario_id:
            context_parts.append(f"usuario_id del paciente: {usuario_id}")
        if state.specialty_id:
            context_parts.append(f"specialty_id: {state.specialty_id}")
        if state.specialty_name:
            context_parts.append(f"especialidad: {state.specialty_name}")
        if state.symptoms_summary:
            context_parts.append(f"sintomas_reportados: {state.symptoms_summary}")
        if state.urgency_level:
            context_parts.append(f"nivel_urgencia: {state.urgency_level}")
        if state.selected_doctor_id:
            context_parts.append(f"medico_id: {state.selected_doctor_id}")
        if state.selected_doctor_name:
            context_parts.append(f"medico: {state.selected_doctor_name}")
        if state.selected_sede_id:
            context_parts.append(f"sede_id: {state.selected_sede_id}")
        if state.selected_sede_name:
            context_parts.append(f"sede: {state.selected_sede_name}")

        context_str = "\n".join(context_parts) if context_parts else "Sin contexto previo."

        # Construir mensaje completo
        full_message = f"## CONTEXTO DEL PACIENTE\n{context_str}\n\n## MENSAJE DEL PACIENTE\n{message}"

        # Agregar historial si existe
        if history:
            history_text = "\n".join(
                f"{'Paciente' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in history[-MAX_HISTORY_MESSAGES:]
            )
            full_message = f"## HISTORIAL\n{history_text}\n\n{full_message}"

        log_event("ORCH", "SCHEDULING", "info", f"Invocando scheduling_agent conv={conversation_id[:8]}")

        try:
            self._scheduling_agent.messages = []
            invocation_state: dict = {}
            response = self._scheduling_agent(full_message, invocation_state=invocation_state)
            provider = _extraer_provider_usado(invocation_state)

            # Extraer texto de la respuesta
            respuesta = str(response)
            if not respuesta or respuesta.strip() == "":
                respuesta = (
                    "No pude procesar tu solicitud de agendamiento. "
                    "Por favor, intenta de nuevo o indica que especialidad necesitas."
                )

            log_event(
                "ORCH", "SCHEDULING", "info",
                f"Respuesta scheduling: {len(respuesta)} chars "
                f"provider={provider}"
            )

            return respuesta

        except Exception as exc:
            log_event("ORCH", "SCHEDULING", "error", f"Error en scheduling_agent: {exc}")
            return (
                "Lo siento, estoy teniendo dificultades tecnicas con el agendamiento. "
                "Por favor, intenta de nuevo en unos minutos."
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
            conversation_id: ID de la conversacion.
            message: Mensaje actual del usuario.
            history: Historial de mensajes [{role, content}, ...].
            usuario_id: ID del usuario autenticado (opcional).
            db: Sesion de SQLAlchemy para persistencia (opcional).

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

        # 1. Clasificar intencion
        intent = classify_intent(message, state)
        previous_agent = state.active_agent

        log_event(
            "ORCH", "INTENT", "info",
            f"Intencion clasificada: {intent} (agente anterior: {previous_agent})"
        )

        # 2. Procesar segun intencion
        if intent == "triage":
            respuesta_texto = await self._process_triage(
                conversation_id, message, history, usuario_id, state
            )
        elif intent == "scheduling":
            # Si viene de triage, inyectar contexto del handoff
            if previous_agent == "triage" and state.specialty_id:
                if not es_uuid_valido(state.specialty_id):
                    uuid_real = await self._resolver_slug(state.specialty_id, state.specialty_name)
                    if uuid_real:
                        state.specialty_id = uuid_real
                    else:
                        state.specialty_id = None

            respuesta_texto = await self._process_scheduling(
                conversation_id, message, history, usuario_id, state
            )
        else:
            # "continue" — mantener agente actual
            if state.active_agent == "scheduling":
                respuesta_texto = await self._process_scheduling(
                    conversation_id, message, history, usuario_id, state
                )
            else:
                respuesta_texto = await self._process_triage(
                    conversation_id, message, history, usuario_id, state
                )

        # 3. Persistir estado
        if db is not None:
            self._persist_state(conversation_id, state, db)

        return respuesta_texto, state

    async def _resolver_slug(
        self, slug: str, specialty_name: str | None
    ) -> str | None:
        """Resuelve un slug de knowledge base a un UUID real del catalogo."""
        from ..agents.tools import obtener_especialidades as _obtener_esp

        if es_uuid_valido(slug):
            return slug

        result_str = _obtener_esp()
        result = json.loads(result_str) if isinstance(result_str, str) else result_str
        if not result.get("ok"):
            return None

        especialidades = result.get("especialidades", [])

        if specialty_name:
            for esp in especialidades:
                if esp.get("nombre", "").lower() == specialty_name.lower():
                    return str(esp.get("especialidad_id", ""))

        slug_normalized = slug.replace("_", " ").lower()
        for esp in especialidades:
            if slug_normalized in esp.get("nombre", "").lower():
                return str(esp.get("especialidad_id", ""))

        return None
