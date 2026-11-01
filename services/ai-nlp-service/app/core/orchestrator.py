from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
import unicodedata
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from strands import Agent
from strands.hooks.events import (
    AfterModelCallEvent,
    AfterToolCallEvent,
    BeforeModelCallEvent,
    BeforeToolCallEvent,
)
from strands.hooks.registry import HookOrder

from .conversation_state import ConversationState, classify_intent, es_uuid_valido
from .conversation_state import BookingDraft, CancelDraft, RescheduleDraft
from .logger import log_event
from .turn_context import TurnContext
from ..knowledge.retrieval import RetrievedKnowledge, retrieve_knowledge

MAX_HISTORY_MESSAGES = 6

_ROUTING_KEY_PREFIX = "strands:model_routing"
ZONA_BOGOTA = ZoneInfo("America/Bogota")
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
BOOKING_DRAFT_TTL = timedelta(minutes=10)
BOOKING_EXECUTION_TIMEOUT = timedelta(seconds=30)
_BOOKING_LOCKS: dict[str, asyncio.Lock] = {}


def _booking_lock(conversation_id: str) -> asyncio.Lock:
    lock = _BOOKING_LOCKS.setdefault(conversation_id, asyncio.Lock())
    if len(_BOOKING_LOCKS) > 1024:
        for key, candidate in list(_BOOKING_LOCKS.items()):
            if candidate is not lock and not candidate.locked():
                _BOOKING_LOCKS.pop(key, None)
                if len(_BOOKING_LOCKS) <= 1024:
                    break
    return lock


def _normalizar_confirmacion(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(
        "".join(char if char.isalnum() or char.isspace() else " " for char in normalized.lower()).split()
    )


def render_booking_summary(draft: BookingDraft) -> str:
    """Renderiza el único resumen confirmable de una reserva."""
    fecha = datetime.strptime(draft.fecha, "%Y-%m-%d").date()
    dia = DIAS_SEMANA[fecha.weekday()]
    motivo = draft.descripcion_sintomas or "Consulta médica"
    return (
        "RESUMEN OFICIAL DE LA CITA\n"
        f"- Especialidad: {draft.especialidad_nombre}\n"
        f"- Fecha: {dia} {fecha.strftime('%d/%m/%Y')}\n"
        f"- Hora: {draft.hora_inicio} - {draft.hora_fin}\n"
        f"- Médico: {draft.medico_nombre}\n"
        f"- Sede: {draft.sede_nombre} ({draft.sede_direccion})\n"
        f"- Motivo: {motivo}\n\n"
        "¿Confirmas?"
    )


MESES_SPANOL = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Mensajes deterministas (por codigo, nunca por LLM) de los flujos PR4.
MENSAJES_NEGACION = {
    "agendar": "Entendido, no agendaré esa cita.",
    "cancelar": "Entendido, no cancelaré esa cita.",
    "reagendar": "Entendido, no reagendaré esa cita.",
}

MENSAJES_CITA_CAMBIO = {
    "cancelar": (
        "Tu cita cambió: ya no está programada (pudo haberse cancelado o "
        "reprogramado por otro medio). Pídeme de nuevo cancelar la cita que quieras."
    ),
    "reagendar": (
        "Tu cita cambió desde que preparé el resumen (ya no está programada "
        "o su horario cambió). Pídeme de nuevo el reagendamiento con la "
        "referencia de la cita."
    ),
}

MENSAJE_CUPO_NO_DISPONIBLE = (
    "Ese horario ya no está disponible. Pídeme de nuevo un reagendamiento "
    "y muestro otras opciones."
)

NOMBRE_ACCION = {"cancelar": "cancelación", "reagendar": "reprogramación"}


def _fecha_larga(fecha_iso: str) -> str:
    """'2026-11-02' -> 'lunes 2 de noviembre de 2026' (sin depender del LLM)."""
    try:
        fecha = datetime.strptime(str(fecha_iso), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return str(fecha_iso)
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.day} de {MESES_SPANOL[fecha.month - 1]} de {fecha.year}"


def _fecha_resumen(fecha_iso: str) -> str:
    """'2026-11-02' -> 'lunes 02/11/2026'; sin LLM y sin lanzar si es corrupta."""
    try:
        fecha = datetime.strptime(str(fecha_iso), "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return str(fecha_iso)
    return f"{DIAS_SEMANA[fecha.weekday()]} {fecha.strftime('%d/%m/%Y')}"


def render_cancel_summary(draft: CancelDraft) -> str:
    """Resumen oficial confirmable de una cancelacion (PR4, paso 6)."""
    motivo = (draft.motivo or "").strip() or "Cancelación solicitada"
    return (
        "RESUMEN OFICIAL DE LA CANCELACIÓN\n"
        "- Acción: CANCELAR\n"
        f"- Fecha: {_fecha_resumen(draft.fecha)}\n"
        f"- Hora: {draft.hora_inicio} - {draft.hora_fin}\n"
        f"- Médico: {draft.medico_nombre}\n"
        f"- Sede: {draft.sede_nombre}\n"
        f"- Especialidad: {draft.especialidad_nombre}\n"
        f"- Motivo: {motivo}\n\n"
        "¿Confirmas? Responde sí o no."
    )


def render_reschedule_summary(draft: RescheduleDraft) -> str:
    """Resumen oficial confirmable de un reagendamiento (PR4, paso 6)."""
    return (
        "RESUMEN OFICIAL DEL REAGENDAMIENTO\n"
        "- Acción: REAGENDAR\n"
        f"- Cita actual: {_fecha_resumen(draft.fecha_original)}, "
        f"de {draft.hora_inicio_original} a {draft.hora_fin_original}\n"
        f"- Nueva fecha: {_fecha_resumen(draft.nueva_fecha)}\n"
        f"- Nueva hora: {draft.nueva_hora_inicio} - {draft.nueva_hora_fin}\n"
        f"- Médico: {draft.medico_nombre}\n"
        f"- Sede: {draft.sede_nombre}\n"
        f"- Especialidad: {draft.especialidad_nombre}\n\n"
        "¿Confirmas? Responde sí o no."
    )


def _resumen_de_accion(state: ConversationState) -> str | None:
    """Resumen oficial del draft activo segun pending_action; None si no hay."""
    if state.pending_action == "cancelar" and state.cancel_draft is not None:
        return render_cancel_summary(state.cancel_draft)
    if state.pending_action == "reagendar" and state.reschedule_draft is not None:
        return render_reschedule_summary(state.reschedule_draft)
    if state.pending_action == "agendar" and state.booking_draft is not None:
        return render_booking_summary(state.booking_draft)
    return None


def _draft_activo(
    state: ConversationState,
) -> BookingDraft | CancelDraft | RescheduleDraft | None:
    if state.pending_action == "cancelar":
        return state.cancel_draft
    if state.pending_action == "reagendar":
        return state.reschedule_draft
    return state.booking_draft


def _limpiar_draft(state: ConversationState) -> None:
    """Limpia el draft activo y toda la ventana de confirmacion."""
    state.booking_draft = None
    state.cancel_draft = None
    state.reschedule_draft = None
    state.pending_action = None
    state.pending_confirmation = False
    state.draft_shown_message_count = None
    state.draft_expires_at = None


def _success_message(draft: BookingDraft) -> str:
    return (
        f"Tu cita de {draft.especialidad_nombre} quedó agendada para el "
        f"{_fecha_larga(draft.fecha)}, de {draft.hora_inicio} a {draft.hora_fin}, "
        f"con {draft.medico_nombre}, en {draft.sede_nombre} ({draft.sede_direccion})."
    )


def _success_cancel_message(draft: CancelDraft) -> str:
    """Exito de cancelacion por codigo, sin UUID."""
    return (
        f"Tu cita de {draft.especialidad_nombre} del {_fecha_larga(draft.fecha)} "
        f"a las {draft.hora_inicio}, con {draft.medico_nombre}, en "
        f"{draft.sede_nombre}, fue cancelada."
    )


def _success_ya_cancelada_message(draft: CancelDraft) -> str:
    """Exito idempotente: la cita ya estaba cancelada, sin UUID."""
    return (
        f"Tu cita de {draft.especialidad_nombre} del {_fecha_larga(draft.fecha)} "
        f"a las {draft.hora_inicio} ya estaba cancelada; no hacía falta "
        "cancelarla de nuevo."
    )


def _success_reschedule_message(draft: RescheduleDraft) -> str:
    """Exito de reagendamiento por codigo, sin UUID."""
    return (
        f"Tu cita de {draft.especialidad_nombre} con {draft.medico_nombre} en "
        f"{draft.sede_nombre} fue reprogramada para el {_fecha_larga(draft.nueva_fecha)}, "
        f"de {draft.nueva_hora_inicio} a {draft.nueva_hora_fin}."
    )


def _is_affirmative(value: str) -> bool:
    words = _normalizar_confirmacion(value).split()
    allowed = {
        "si", "sii", "claro", "dale", "ok", "listo", "confirmo",
        "confirmar", "agendala", "agendalo", "por", "favor",
        "de", "acuerdo", "correcto", "perfecto",
    }
    strong = {"si", "sii", "confirmo", "agendala", "agendalo", "dale", "ok", "listo"}
    return bool(words) and all(word in allowed for word in words) and bool(set(words) & strong)


def _is_explicit_authorization(value: str) -> bool:
    normalized = _normalizar_confirmacion(value)
    if "?" in value or normalized.startswith(("no la", "no quiero", "no agendes")):
        return False
    return any(phrase in normalized for phrase in {
        "agendala de una vez",
        "no esperes mi confirmacion",
        "decide tu y agendala",
    })


def _is_unambiguous_negative(value: str) -> bool:
    return _normalizar_confirmacion(value) in {
        "no",
        "no la agendes",
        "cancela la propuesta",
        "ya no",
    }


def _menciona_autorizacion_apurada(value: str) -> bool:
    """True si el usuario pide saltarse la confirmacion ("de una vez", etc.).

    Solo se usa para CANCELAR/REAGENDAR: ahi nunca ejecuta, solo vuelve a
    mostrar el resumen oficial. Para "agendar" esa decision la toma
    _is_explicit_authorization.
    """
    normalized = _normalizar_confirmacion(value)
    if "?" in value or normalized.startswith(("no la", "no quiero")):
        return False
    return any(
        phrase in normalized
        for phrase in {
            "de una vez",
            "sin esperar confirmacion",
            "no esperes confirmacion",
            "no esperes mi confirmacion",
        }
    )


def _registrar_hook_provider(agent: Agent) -> None:
    """Registra un hook que captura el proveedor LLM usado en cada invocación.

    El hook se ejecuta en AfterModelCallEvent (order=60, después del
    _on_model_result del router en order=50). Lee el _RoutingState de
    invocation_state y almacena candidate.name en agent._provider_used.
    """

    def _provider_name(invocation_state: dict[str, Any]) -> str:
        for key, value in invocation_state.items():
            if key.startswith(_ROUTING_KEY_PREFIX):
                candidate = getattr(value, "candidate", None)
                if candidate is not None:
                    return getattr(candidate, "name", "unknown")
        return "unknown"

    def _capturar_provider(event: AfterModelCallEvent) -> None:
        agent._provider_used = _provider_name(event.invocation_state)
        metrics = event.invocation_state.get("scheduling_metrics")
        if metrics is not None:
            elapsed = (time.perf_counter() - metrics.pop("_model_started_at", time.perf_counter())) * 1000
            metrics["llm_ms"] += elapsed
            exception = event.exception
            metrics["provider_attempts"].append({
                "provider": agent._provider_used,
                "status": "429" if exception and "429" in str(exception) else (
                    "error" if exception else "ok"
                ),
                "ms": round(elapsed),
            })

    def _before_model(event: BeforeModelCallEvent) -> None:
        metrics = event.invocation_state.get("scheduling_metrics")
        if metrics is not None:
            metrics["_model_started_at"] = time.perf_counter()

    def _before_tool(event: BeforeToolCallEvent) -> None:
        metrics = event.invocation_state.get("scheduling_metrics")
        if metrics is not None:
            metrics.setdefault("_tool_started_at", {})[
                event.tool_use.get("toolUseId", str(id(event)))
            ] = time.perf_counter()

    def _after_tool(event: AfterToolCallEvent) -> None:
        metrics = event.invocation_state.get("scheduling_metrics")
        if metrics is not None:
            tool_id = event.tool_use.get("toolUseId", str(id(event)))
            started = metrics.setdefault("_tool_started_at", {}).pop(tool_id, None)
            if started is not None:
                metrics["tools_ms"] += (time.perf_counter() - started) * 1000

    agent.hooks.add_callback(BeforeModelCallEvent, _before_model, order=40)
    agent.hooks.add_callback(BeforeToolCallEvent, _before_tool, order=40)
    agent.hooks.add_callback(AfterToolCallEvent, _after_tool, order=40)

    agent.hooks.add_callback(AfterModelCallEvent, _capturar_provider, order=60)


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
        _registrar_hook_provider(triage_agent)
        _registrar_hook_provider(scheduling_agent)

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

    def _build_system_context(
        self, state: ConversationState, usuario_id: str | None
    ) -> str:
        """Construye el unico contexto runtime inyectado al agente."""
        ahora_bogota = datetime.now(ZONA_BOGOTA)
        fecha_actual = (
            f"{ahora_bogota.strftime('%Y-%m-%d')} "
            f"({DIAS_SEMANA[ahora_bogota.weekday()]})"
        )
        parts: list[str] = [
            f"Fecha actual del sistema: {fecha_actual}. "
            "No propongas ni consultes fechas anteriores a esta."
        ]
        if usuario_id:
            parts.append(f"usuario_id del paciente: {usuario_id}")
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
        if state.selected_sede_id:
            parts.append(f"sede_id: {state.selected_sede_id}")
        if state.selected_sede_name:
            parts.append(f"sede: {state.selected_sede_name}")
        return "\n".join(parts)

    async def _process_triage(
        self,
        conversation_id: str,
        message: str,
        history: list[dict[str, str]],
        usuario_id: str | None,
        state: ConversationState,
        retrieved_knowledge: list[RetrievedKnowledge] | None = None,
    ) -> str:
        """Procesa un mensaje con el agente de triaje.

        El agente retorna TriageAnalysis estructurado directamente.
        """
        state.active_agent = "triage"

        # Construir contexto RAG solo para esta invocacion.
        rag_context = ""
        if retrieved_knowledge:
            rag_fragments = "\n\n".join(
                (
                    f"Fragmento {index}\n"
                    f"Tipo: {chunk.tipo}\n"
                    f"Nombre: {chunk.nombre or 'Sin nombre'}\n"
                    f"Similitud: {chunk.similitud}\n"
                    f"Contenido:\n{chunk.contenido}"
                )
                for index, chunk in enumerate(retrieved_knowledge, start=1)
            )
            rag_context = (
                "## CONTEXTO RAG — APOYO PARA EL TRIAJE\n"
                f"{rag_fragments}\n\n"
                "## REGLAS DE USO DEL CONTEXTO RAG\n"
                "- Usa estos fragmentos como orientacion, no como diagnostico.\n"
                "- No inventes informacion que no aparezca en los datos del paciente.\n"
                "- Si falta informacion clinica, indica que se necesita aclaracion.\n"
                "- Mantén siempre las reglas de seguridad medica del system prompt.\n"
                "- No muestres al paciente scores, IDs ni contenido interno de recuperacion.\n"
            )

        # Construir mensaje con contexto RAG e historial
        full_message = message
        if rag_context:
            full_message = f"{rag_context}\n## MENSAJE ACTUAL DEL PACIENTE\n{message}"
        if history:
            history_text = "\n".join(
                f"{'Paciente' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in history[-MAX_HISTORY_MESSAGES:]
            )
            current_message = (
                full_message
                if rag_context
                else f"Mensaje actual del paciente: {message}"
            )
            full_message = (
                f"Historial de la conversacion:\n{history_text}\n\n{current_message}"
            )

        log_event("ORCH", "TRIAGE", "info", f"Invocando triage_agent conv={conversation_id[:8]}")

        try:
            self._triage_agent.messages = []
            response = self._triage_agent(full_message)
            provider = getattr(self._triage_agent, "_provider_used", "unknown")

            # Extraer clasificación (Pydantic, dict o JSON crudo)
            classification = _extraer_clasificacion(response)
            fallback_notice = None

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

                # Normalizar specialty_id antes de persistirlo o hacer handoff.
                raw_specialty_id = str(esp_id) if esp_id else None
                resolved_specialty_id = raw_specialty_id
                if raw_specialty_id and not es_uuid_valido(raw_specialty_id):
                    resolved_specialty_id = await self._resolver_slug(
                        raw_specialty_id, esp_nombre
                    )
                fallback_notice = None
                if not resolved_specialty_id and (esp_nombre or raw_specialty_id):
                    fallback_specialty_id = await self._resolver_slug(
                        "", "Medicina General"
                    )
                    if fallback_specialty_id:
                        fallback_notice = (
                            f"Nota: {esp_nombre or raw_specialty_id} no está disponible "
                            "por ahora; puedo agendarte con Medicina General, que puede "
                            "remitirte."
                        )
                        resolved_specialty_id = fallback_specialty_id
                        esp_nombre = "Medicina General"
                        log_event(
                            "ORCH",
                            "SPECIALTY_FALLBACK",
                            "warning",
                            "Especialidad no disponible; usando Medicina General",
                        )
                    else:
                        fallback_notice = (
                            f"No pude encontrar {esp_nombre or raw_specialty_id or 'esa especialidad'} "
                            "en el catálogo y Medicina General tampoco está disponible."
                        )
                        log_event(
                            "ORCH",
                            "SPECIALTY_FALLBACK",
                            "error",
                            "No se pudo resolver Medicina General en el catálogo",
                        )
                log_event(
                    "ORCH", "TRIAGE", "debug",
                    f"specialty_id crudo={raw_specialty_id!r}, "
                    f"resuelto={resolved_specialty_id!r}",
                )
                if raw_specialty_id and not resolved_specialty_id:
                    log_event(
                        "ORCH", "TRIAGE", "warning",
                        f"No se pudo resolver specialty_id={raw_specialty_id!r}",
                    )

                # Actualizar estado (incluir symptoms_summary explícitamente)
                state.specialty_id = resolved_specialty_id if es_uuid_valido(
                    resolved_specialty_id or ""
                ) else None
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
            if fallback_notice:
                respuesta = f"{respuesta}\n\n{fallback_notice}"

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

        Strands ejecuta las tools (obtener_medicos, proponer_cita, etc.)
        de forma autónoma en un loop interno.
        """
        state.active_agent = "scheduling"

        # Construir mensaje completo
        context_str = self._build_system_context(state, usuario_id)
        full_message = f"## CONTEXTO DEL PACIENTE\n{context_str}\n\n## MENSAJE DEL PACIENTE\n{message}"

        # Agregar historial si existe
        if history:
            history_text = "\n".join(
                f"{'Paciente' if m['role'] == 'user' else 'Asistente'}: {m['content']}"
                for m in history[-MAX_HISTORY_MESSAGES:]
            )
            full_message = f"## HISTORIAL\n{history_text}\n\n{full_message}"

        log_event("ORCH", "SCHEDULING", "info", f"Invocando scheduling_agent conv={conversation_id[:8]}")

        turn_context = TurnContext(conversation_id, usuario_id, state)
        turn_started_at = time.perf_counter()
        scheduling_metrics: dict[str, Any] = {
            "llm_ms": 0.0,
            "tools_ms": 0.0,
            "provider_attempts": [],
        }
        try:
            self._scheduling_agent.messages = []
            invocation_state = {
                "conversation_id": conversation_id,
                "usuario_id": usuario_id,
                "state": state,
                "turn_context": turn_context,
                "scheduling_metrics": scheduling_metrics,
            }
            signature = inspect.signature(self._scheduling_agent.__call__)
            supports_invocation_state = (
                "invocation_state" in signature.parameters
                or any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in signature.parameters.values()
                )
            )
            if supports_invocation_state:
                response = self._scheduling_agent(
                    full_message, invocation_state=invocation_state
                )
            else:
                response = self._scheduling_agent(full_message)
            provider = getattr(self._scheduling_agent, "_provider_used", "unknown")

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
                f"provider={provider} "
                f"latency_ms={round((time.perf_counter() - turn_started_at) * 1000)} "
                f"llm_ms={round(scheduling_metrics['llm_ms'])} "
                f"tools_ms={round(scheduling_metrics['tools_ms'])} "
                f"provider_attempts={scheduling_metrics['provider_attempts']}"
            )

            if state.pending_action is not None:
                respuesta = self._append_booking_summary(state, respuesta)
            elif (
                state.last_options_message_count == state.message_count - 1
                and re.search(r"\b\d{1,2}:\d{2}\b|\b\d{1,2}\s*(?:am|pm)\b", message.lower())
            ):
                log_event(
                    "ORCH",
                    "ALERT",
                    "warning",
                    f"scheduling.selection_without_draft conv={conversation_id[:8]}",
                )
            if any(
                marker in respuesta.lower()
                for marker in ("horarios disponibles", "opciones disponibles", "cuál de estos")
            ):
                state.last_options_message_count = state.message_count
            return respuesta

        except Exception as exc:
            turn_context.rollback()
            log_event(
                "ORCH",
                "SCHEDULING",
                "error",
                f"Error en scheduling_agent: {exc} "
                f"latency_ms={round((time.perf_counter() - turn_started_at) * 1000)} "
                f"llm_ms={round(scheduling_metrics['llm_ms'])} "
                f"tools_ms={round(scheduling_metrics['tools_ms'])} "
                f"provider_attempts={scheduling_metrics['provider_attempts']}",
            )
            return (
                "Lo siento, estoy teniendo dificultades tecnicas con el agendamiento. "
                "Por favor, intenta de nuevo en unos minutos."
            )

    def _append_booking_summary(self, state: ConversationState, response: str) -> str:
        """Añade o reemplaza el bloque oficial del draft activo y marca cuándo se mostró.

        Dispatch por pending_action (PR4 paso 6): agendar, cancelar o
        reagendar. Usa el marker generico "RESUMEN OFICIAL" para no duplicar
        texto si ya hay un resumen (de cualquier tipo) en la respuesta.
        """
        summary = _resumen_de_accion(state)
        if summary is None:
            return response
        base = response.split("RESUMEN OFICIAL", 1)[0].rstrip()
        state.draft_shown_message_count = state.message_count
        state.draft_expires_at = (
            datetime.now(ZONA_BOGOTA) + BOOKING_DRAFT_TTL
        ).isoformat()
        state.pending_confirmation = True
        return f"{base}\n\n{summary}" if base else summary

    def _refrescar_ventana_draft(self, state: ConversationState) -> None:
        """Vuelve a abrir la ventana de confirmacion (reintento tras fallo)."""
        state.draft_shown_message_count = state.message_count
        state.draft_expires_at = (
            datetime.now(ZONA_BOGOTA) + BOOKING_DRAFT_TTL
        ).isoformat()
        state.pending_confirmation = True

    def _remostrar_resumen(self, state: ConversationState) -> str:
        """Re-muestra el resumen oficial del draft activo (sin ejecutar)."""
        self._refrescar_ventana_draft(state)
        return _resumen_de_accion(state) or ""

    def _draft_is_expired(self, state: ConversationState) -> bool:
        if not state.draft_expires_at:
            return True
        try:
            expires_at = datetime.fromisoformat(state.draft_expires_at)
        except ValueError:
            return True
        return datetime.now(ZONA_BOGOTA) >= expires_at

    def _user_id_is_valid_for_draft(
        self, usuario_id: str | None, draft: BookingDraft | CancelDraft | RescheduleDraft
    ) -> bool:
        try:
            current = UUID(str(usuario_id))
            expected = UUID(draft.usuario_id)
        except (TypeError, ValueError):
            return False
        return current.int != 0 and expected.int != 0 and current == expected

    async def _execute_booking(
        self,
        conversation_id: str,
        state: ConversationState,
        usuario_id: str | None,
        db: Session | None,
    ) -> str | None:
        draft = state.booking_draft
        if draft is None or not draft.is_complete():
            log_event("ORCH", "BOOKING", "warning", "rejected: draft incompleto")
            return None
        if not self._user_id_is_valid_for_draft(usuario_id, draft):
            log_event("ORCH", "BOOKING", "warning", "rejected: usuario invalido")
            return None

        lock = _booking_lock(conversation_id)
        async with lock:
            if state.last_booking_id and state.last_booking_summary:
                log_event("ORCH", "BOOKING", "info", "execute: confirmacion repetida")
                return state.last_booking_summary
            if state.execution_started_at:
                try:
                    started = datetime.fromisoformat(state.execution_started_at)
                    if datetime.now(ZONA_BOGOTA) - started < BOOKING_EXECUTION_TIMEOUT:
                        log_event("ORCH", "BOOKING", "warning", "rejected: execution en curso")
                        return "La reserva ya está siendo procesada. Por favor espera un momento."
                except ValueError:
                    pass

            state.execution_started_at = datetime.now(ZONA_BOGOTA).isoformat()
            if db is not None:
                self._persist_state(conversation_id, state, db)

            try:
                from ..agents.tools import crear_cita_desde_draft

                result = await asyncio.to_thread(crear_cita_desde_draft, draft)
                if result.get("ok"):
                    message = _success_message(draft)
                    state.last_booking_id = result.get("cita_id") or "confirmed"
                    state.last_booking_summary = message
                    _limpiar_draft(state)
                    log_event("ORCH", "BOOKING", "info", "execute: reserva exitosa")
                    return message

                self._refrescar_ventana_draft(state)
                log_event("ORCH", "BOOKING", "warning", "execute: servicio rechazo la reserva")
                return "No pude completar la reserva. Tu propuesta sigue guardada; confirma de nuevo para reintentar."
            finally:
                state.execution_started_at = None
                if db is not None:
                    self._persist_state(conversation_id, state, db)

    @staticmethod
    def _reverificar_cita_del_draft(
        draft: CancelDraft | RescheduleDraft, usuario_id: str | None, action: str
    ) -> dict[str, Any]:
        """Reconsulta las citas ACTIVAS del usuario verificado antes de ejecutar.

        Regla PR4 paso 7: nunca ejecutar cancelar/reagendar contra una cita
        que cambio o fue cancelada por otro canal entre la propuesta y el "si".

        Returns:
            {"ok": True} si la cita sigue programada (y al reagendar, con la
            fecha/hora ORIGINALES del draft);
            {"ok": False, "cita_cambio": True} si cambio/cancelo por otro canal;
            {"ok": False, "error": ...} si la consulta fallo (transitorio: el
            draft se conserva para reintentar).
        """
        from ..agents.tools import _obtener_citas_activas

        resultado = _obtener_citas_activas(usuario_id or "")
        if not resultado.get("ok"):
            return {
                "ok": False,
                "error": resultado.get("error") or "No pude consultar tus citas.",
            }
        cita_id = str(draft.cita_id)
        for cita in resultado.get("citas", []):
            if not isinstance(cita, dict) or str(cita.get("cita_id")) != cita_id:
                continue
            if action == "reagendar":
                fecha_actual = str(cita.get("fecha_cita", ""))[:10]
                hora_actual = str(cita.get("hora_inicio", ""))[:5]
                if (
                    fecha_actual != str(draft.fecha_original)[:10]
                    or hora_actual != str(draft.hora_inicio_original)[:5]
                ):
                    return {"ok": False, "cita_cambio": True}
            return {"ok": True}
        # No figura entre las programadas: la cancelaron o reprogramaron por
        # otro medio (o la cita dejo de existir).
        return {"ok": False, "cita_cambio": True}

    async def _ejecutar_cancelar_reagendar(
        self,
        conversation_id: str,
        state: ConversationState,
        usuario_id: str | None,
        db: Session | None,
        action: str,
    ) -> str | None:
        """Ejecuta cancelar/reagendar tras el 'si' determinista (PR4 paso 7)."""
        draft: CancelDraft | RescheduleDraft | None = (
            state.cancel_draft if action == "cancelar" else state.reschedule_draft
        )
        if draft is None:
            return None

        lock = _booking_lock(conversation_id)
        async with lock:
            if state.last_booking_id and state.last_booking_summary:
                log_event("ORCH", "BOOKING", "info", f"{action}: confirmacion repetida")
                return state.last_booking_summary
            if state.execution_started_at:
                try:
                    started = datetime.fromisoformat(state.execution_started_at)
                    if datetime.now(ZONA_BOGOTA) - started < BOOKING_EXECUTION_TIMEOUT:
                        log_event("ORCH", "BOOKING", "warning", f"{action}: rejected: execution en curso")
                        return "La operación ya está siendo procesada. Por favor espera un momento."
                except ValueError:
                    pass

            state.execution_started_at = datetime.now(ZONA_BOGOTA).isoformat()
            if db is not None:
                self._persist_state(conversation_id, state, db)

            try:
                verificacion = await asyncio.to_thread(
                    self._reverificar_cita_del_draft, draft, usuario_id, action
                )
                if verificacion.get("cita_cambio"):
                    _limpiar_draft(state)
                    log_event("ORCH", "BOOKING", "info", f"{action}: rejected: la cita cambio")
                    return MENSAJES_CITA_CAMBIO[action]
                if not verificacion.get("ok"):
                    # Fallo transitorio de la consulta: draft intacto, reintentable.
                    self._refrescar_ventana_draft(state)
                    log_event(
                        "ORCH", "BOOKING", "warning",
                        f"{action}: verificacion fallo: {verificacion.get('error')}",
                    )
                    return (
                        "No pude verificar tu cita ahora mismo. Tu propuesta sigue "
                        "guardada; confirma de nuevo para reintentar."
                    )

                from ..agents.tools import (
                    ejecutar_cancelacion_desde_draft,
                    ejecutar_reagendamiento_desde_draft,
                )

                executor = (
                    ejecutar_cancelacion_desde_draft
                    if action == "cancelar"
                    else ejecutar_reagendamiento_desde_draft
                )
                result = await asyncio.to_thread(executor, draft, usuario_id or "")
                if result.get("ok"):
                    if action == "cancelar":
                        message = (
                            _success_ya_cancelada_message(draft)
                            if result.get("ya_cancelada")
                            else _success_cancel_message(draft)
                        )
                    else:
                        message = _success_reschedule_message(draft)
                    state.last_booking_id = draft.cita_id
                    state.last_booking_summary = message
                    _limpiar_draft(state)
                    log_event("ORCH", "BOOKING", "info", f"{action}: ejecucion exitosa")
                    return message
                if result.get("cupo_no_disponible"):
                    _limpiar_draft(state)
                    log_event("ORCH", "BOOKING", "info", f"{action}: cupo ya no disponible")
                    return MENSAJE_CUPO_NO_DISPONIBLE
                if result.get("cita_cambio"):
                    _limpiar_draft(state)
                    log_event("ORCH", "BOOKING", "info", f"{action}: la cambio en la ejecucion")
                    return MENSAJES_CITA_CAMBIO[action]

                # Fallo transitorio (ok False sin banderas): conservar el draft
                # y refrescar la ventana para que el "si" siguiente reintente.
                self._refrescar_ventana_draft(state)
                log_event(
                    "ORCH", "BOOKING", "warning",
                    f"{action}: fallo transitorio: {result.get('error')}",
                )
                return (
                    f"No pude completar la {NOMBRE_ACCION[action]}. Tu propuesta "
                    "sigue guardada; confirma de nuevo para reintentar o pídeme "
                    "otra hora."
                )
            finally:
                state.execution_started_at = None
                if db is not None:
                    self._persist_state(conversation_id, state, db)

    async def _handle_pending_action(
        self,
        conversation_id: str,
        message: str,
        usuario_id: str | None,
        state: ConversationState,
        db: Session | None,
    ) -> str | None:
        """Resuelve confirmaciones (agendar/cancelar/reagendar) antes de clasificar.

        Solo "_is_affirmative" ejecuta. "_is_explicit_authorization" ejecuta
        SOLO para "agendar"; en cancelar/reagendar ("de una vez", "no esperes
        confirmacion") nunca ejecuta: se vuelve a mostrar el resumen oficial.
        """
        if (
            state.last_booking_id or state.last_booking_summary
        ) and not _is_affirmative(message):
            state.last_booking_id = None
            state.last_booking_summary = None
        if state.last_booking_summary and not state.pending_action:
            if _is_affirmative(message):
                log_event("ORCH", "BOOKING", "info", "execute: confirmacion repetida tras exito")
                return state.last_booking_summary
            return None
        action = state.pending_action
        draft = _draft_activo(state)
        if action is None or draft is None:
            return None
        if _is_unambiguous_negative(message):
            _limpiar_draft(state)
            log_event("ORCH", "BOOKING", "info", "rejected: negacion del usuario")
            return MENSAJES_NEGACION[action]
        if self._draft_is_expired(state):
            log_event("ORCH", "BOOKING", "warning", "expired: draft fuera de TTL")
            _limpiar_draft(state)
            return None

        if action in ("cancelar", "reagendar"):
            cita_id = str(getattr(draft, "cita_id", "") or "").strip()
            if not cita_id or not self._user_id_is_valid_for_draft(usuario_id, draft):
                # Draft corrupto (cita_id vacio) o de OTRO usuario: nunca se
                # ejecuta y se limpia.
                log_event(
                    "ORCH", "BOOKING", "warning",
                    f"rejected: {action} con cita_id vacio o usuario distinto",
                )
                _limpiar_draft(state)
                return None
            if state.draft_shown_message_count != state.message_count - 1:
                log_event("ORCH", "BOOKING", "info", "stale: resumen no corresponde al turno anterior")
                return None
            if not _is_affirmative(message):
                if _menciona_autorizacion_apurada(message):
                    # Cancelar/reagendar NUNCA se ejecutan por autorizacion
                    # apurada: solo se vuelve a mostrar el resumen oficial.
                    log_event(
                        "ORCH", "BOOKING", "info",
                        f"re-show: autorizacion apurada no ejecuta en {action}",
                    )
                    return self._remostrar_resumen(state)
                log_event("ORCH", "BOOKING", "info", "ambiguous: pasa al agente con draft intacto")
                return None
            log_event("ORCH", "BOOKING", "info", f"execute: confirmacion determinista ({action})")
            return await self._ejecutar_cancelar_reagendar(
                conversation_id, state, usuario_id, db, action
            )

        # action == "agendar" (comportamiento pre-PR4, sin cambios).
        if state.draft_shown_message_count != state.message_count - 1:
            log_event("ORCH", "BOOKING", "info", "stale: resumen no corresponde al turno anterior")
            return None
        if not self._user_id_is_valid_for_draft(usuario_id, state.booking_draft):
            log_event("ORCH", "BOOKING", "warning", "rejected: usuario distinto o UUID cero")
            return None
        if _is_affirmative(message):
            log_event("ORCH", "BOOKING", "info", "execute: confirmacion determinista")
            return await self._execute_booking(conversation_id, state, usuario_id, db)
        if _is_explicit_authorization(message):
            log_event("ORCH", "BOOKING", "info", "execute: autorizacion explicita mismo turno")
            return await self._execute_booking(conversation_id, state, usuario_id, db)
        log_event("ORCH", "BOOKING", "info", "ambiguous: pasa al agente con draft intacto")
        return None

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

        pending_response = await self._handle_pending_action(
            conversation_id, message, usuario_id, state, db
        )
        if pending_response is not None:
            if db is not None:
                self._persist_state(conversation_id, state, db)
            return pending_response, state

        # 1. Recuperar contexto y clasificar intencion
        retrieved_knowledge = retrieve_knowledge(db, message) if db is not None else []
        semantic_clinical = bool(retrieved_knowledge)
        intent = classify_intent(message, state, semantic_clinical=semantic_clinical)
        previous_agent = state.active_agent

        log_event(
            "ORCH", "INTENT", "info",
            f"Intencion clasificada: {intent} (agente anterior: {previous_agent}, "
            f"rag={'si' if semantic_clinical else 'no'})"
        )

        # 2. Procesar segun intencion
        if intent == "triage":
            respuesta_texto = await self._process_triage(
                conversation_id,
                message,
                history,
                usuario_id,
                state,
                retrieved_knowledge,
            )
        elif intent == "scheduling" or (
            intent == "continue" and state.active_agent == "scheduling"
        ):
            # Normalizar cualquier estado antiguo antes de invocar el agente.
            if state.specialty_id and not es_uuid_valido(state.specialty_id):
                uuid_real = await self._resolver_slug(
                    state.specialty_id, state.specialty_name, message
                )
                state.specialty_id = (
                    uuid_real if uuid_real and es_uuid_valido(uuid_real) else None
                )

            if not state.specialty_id:
                uuid_real = await self._resolver_slug(
                    "", state.specialty_name, message
                )
                if not uuid_real and state.specialty_name:
                    uuid_real = await self._resolver_slug("", "Medicina General")
                    if uuid_real:
                        original_specialty = state.specialty_name
                        state.specialty_id = uuid_real
                        state.specialty_name = "Medicina General"
                        log_event(
                            "ORCH",
                            "SPECIALTY_FALLBACK",
                            "warning",
                            "Especialidad del estado no disponible; usando Medicina General",
                        )
                        respuesta_texto = (
                            f"Nota: {original_specialty} no está disponible por ahora; "
                            "puedo agendarte con Medicina General, que puede remitirte."
                        )
                        respuesta_texto += "\n\n" + await self._process_scheduling(
                            conversation_id, message, history, usuario_id, state
                        )
                        if db is not None:
                            self._persist_state(conversation_id, state, db)
                        return respuesta_texto, state
                if uuid_real:
                    state.specialty_id = uuid_real
                    state.active_agent = "scheduling"
                else:
                    if state.symptoms_summary or state.specialty_name:
                        respuesta_texto = (
                            "No pude encontrar una especialidad disponible para tu solicitud. "
                            "Por favor, intenta con otra especialidad."
                        )
                        if db is not None:
                            self._persist_state(conversation_id, state, db)
                        return respuesta_texto, state
                    state.active_agent = "triage"
                    respuesta_texto = (
                        "Para ayudarte a agendar necesito conocer primero tus sintomas "
                        "o la especialidad que necesitas."
                    )
                    if db is not None:
                        self._persist_state(conversation_id, state, db)
                    return respuesta_texto, state

            respuesta_texto = await self._process_scheduling(
                conversation_id, message, history, usuario_id, state
            )
            if (
                state.booking_draft is not None
                and _is_explicit_authorization(message)
            ):
                log_event(
                    "ORCH",
                    "BOOKING",
                    "info",
                    "execute: autorizacion explicita en turno de propuesta",
                )
                executed = await self._execute_booking(
                    conversation_id, state, usuario_id, db
                )
                if executed is not None:
                    respuesta_texto = executed
        else:
            # "continue" — mantener agente actual
            respuesta_texto = await self._process_triage(
                conversation_id,
                message,
                history,
                usuario_id,
                state,
                retrieved_knowledge,
            )

        # 3. Persistir estado
        if db is not None:
            self._persist_state(conversation_id, state, db)

        return respuesta_texto, state

    async def _resolver_slug(
        self, slug: str, specialty_name: str | None, message: str | None = None
    ) -> str | None:
        """Resuelve una especialidad por UUID, nombre o slug sin usar el LLM."""
        from ..agents.tools import (
            _consultar_catalog_service_cached,
            obtener_especialidades as _obtener_esp,
        )

        if es_uuid_valido(slug):
            return slug

        result_str = _obtener_esp()
        result = json.loads(result_str) if isinstance(result_str, str) else result_str
        if not result.get("ok"):
            return None

        especialidades = result.get("especialidades", [])
        servicios_result = _consultar_catalog_service_cached("/servicios")
        servicios = servicios_result.get("data", []) if servicios_result.get("ok") else []
        nombres_servicios = {
            str(servicio.get("servicio_id")): str(servicio.get("nombre", ""))
            for servicio in servicios
        }

        def _normalizar(value: str) -> str:
            sin_tildes = unicodedata.normalize("NFKD", value)
            sin_tildes = "".join(
                char for char in sin_tildes if not unicodedata.combining(char)
            )
            return " ".join(sin_tildes.lower().replace("_", " ").split())

        candidatos: list[dict[str, Any]] = []
        consulta = _normalizar(message or "")
        nombres_consultables = [
            _normalizar(value)
            for value in (specialty_name, slug.replace("_", " "))
            if value
        ]
        for esp in especialidades:
            nombre = _normalizar(str(esp.get("nombre", "")))
            if not nombre:
                continue
            nombre_sin_prefijo = nombre
            for prefijo in ("consulta ", "servicio "):
                if nombre_sin_prefijo.startswith(prefijo):
                    nombre_sin_prefijo = nombre_sin_prefijo[len(prefijo):]
                    break
            nombres_catalogo = {
                nombre,
                nombre_sin_prefijo,
                _normalizar(nombres_servicios.get(str(esp.get("servicio_id")), "")),
            }
            if any(
                candidato in nombres_catalogo
                or any(
                    candidato and candidato in nombre_catalogo_item
                    for nombre_catalogo_item in nombres_catalogo
                )
                for candidato in nombres_consultables
            ) or (
                consulta
                and any(
                    nombre_catalogo_item and nombre_catalogo_item in consulta
                    for nombre_catalogo_item in nombres_catalogo
                )
            ):
                candidatos.append(esp)

        ids = {
            str(esp.get("especialidad_id", ""))
            for esp in candidatos
            if es_uuid_valido(str(esp.get("especialidad_id", "")))
        }
        if len(ids) == 1:
            return ids.pop()
        if len(ids) > 1:
            log_event(
                "ORCH",
                "SPECIALTY_RESOLVE",
                "warning",
                f"Especialidad ambigua para consulta={message or slug!r}: {len(ids)} coincidencias",
            )

        return None
