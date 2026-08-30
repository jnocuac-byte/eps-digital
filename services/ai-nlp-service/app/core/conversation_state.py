from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

TRIAGE_KEYWORDS = [
    "dolor",
    "fiebre",
    "tos",
    "malestar",
    "síntoma",
    "sintoma",
    "enfermedad",
    "duele",
    "molestia",
    "cabeza",
    "estómago",
    "pecho",
    "respirar",
    "náusea",
    "nausea",
    "vómito",
    "vomito",
    "mareo",
    "sangrado",
    "presión",
    "presion",
    "cardíaco",
    "cardiaco",
    "inchazón",
    "hinchazon",
    "erupción",
    "erupcion",
    "picazón",
    "picazon",
    "fiebre",
    "escalofríos",
    "escalofrios",
    "fatiga",
    "cansancio",
    "insomnio",
    "ansiedad",
    "depresión",
    "depresion",
]

SCHEDULING_KEYWORDS = [
    "cita",
    "agendar",
    "disponibilidad",
    "horario",
    "doctor",
    "médico",
    "medico",
    "reservar",
    "turno",
    "consultorio",
    "agenda",
    "schedule",
    "booking",
    "fecha para",
    "cuándo puedo",
    "cuando puedo",
]


@dataclass
class ConversationState:
    """Estado persistente de una conversación multi-agente."""

    active_agent: Literal["idle", "triage", "scheduling"] = "idle"

    # Contexto del triage (se hereda al scheduling)
    specialty_id: str | None = None
    specialty_name: str | None = None
    symptoms_summary: str | None = None
    urgency_level: Literal["urgente", "prioritario", "programable"] | None = None
    red_flag_detected: bool = False

    # Contexto del agendamiento
    selected_doctor_id: str | None = None
    selected_doctor_name: str | None = None
    selected_sede_id: str | None = None
    selected_sede_name: str | None = None
    selected_date: str | None = None
    selected_time: str | None = None
    pending_confirmation: bool = False

    # Metadata
    message_count: int = 0
    handoff_context: dict | None = None

    def to_system_context(self) -> str:
        """Serializa el estado como contexto inyectable en el prompt del agente."""
        parts: list[str] = []
        if self.specialty_name:
            parts.append(f"Especialidad identificada: {self.specialty_name}")
        if self.symptoms_summary:
            parts.append(f"Síntomas reportados: {self.symptoms_summary}")
        if self.urgency_level:
            parts.append(f"Nivel de urgencia: {self.urgency_level}")
        if self.selected_doctor_name:
            parts.append(f"Médico seleccionado: {self.selected_doctor_name}")
        if self.selected_sede_name:
            parts.append(f"Sede seleccionada: {self.selected_sede_name}")
        if self.selected_date:
            parts.append(f"Fecha seleccionada: {self.selected_date}")
        if self.selected_time:
            parts.append(f"Hora seleccionada: {self.selected_time}")
        return "\n".join(parts) if parts else "Sin contexto previo."


def classify_intent(
    message: str, state: ConversationState
) -> Literal["triage", "scheduling", "continue"]:
    """Clasifica la intención del usuario para enrutar al agente correcto.

    Returns:
        "triage"      → routed to TriageAgent
        "scheduling"  → routed to SchedulingAgent
        "continue"    → keep current agent
    """
    msg = message.lower().strip()

    # Palabras clave de agendamiento siempre ganan (intención explícita)
    if any(kw in msg for kw in SCHEDULING_KEYWORDS):
        return "scheduling"

    # Palabras clave médicas → triage
    if any(kw in msg for kw in TRIAGE_KEYWORDS):
        return "triage"

    # Sin señal clara → continuar con agente actual
    if state.active_agent != "idle":
        return "continue"

    # Default: triage (primera interacción más común)
    return "triage"
