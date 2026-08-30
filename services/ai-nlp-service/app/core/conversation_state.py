from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
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

    def to_dict(self) -> dict:
        """Serializa el estado a un diccionario JSON-compatible."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ConversationState:
        """Reconstruye un ConversationState desde un diccionario serializado."""
        return cls(
            active_agent=data.get("active_agent", "idle"),
            specialty_id=data.get("specialty_id"),
            specialty_name=data.get("specialty_name"),
            symptoms_summary=data.get("symptoms_summary"),
            urgency_level=data.get("urgency_level"),
            red_flag_detected=data.get("red_flag_detected", False),
            selected_doctor_id=data.get("selected_doctor_id"),
            selected_doctor_name=data.get("selected_doctor_name"),
            selected_sede_id=data.get("selected_sede_id"),
            selected_sede_name=data.get("selected_sede_name"),
            selected_date=data.get("selected_date"),
            selected_time=data.get("selected_time"),
            pending_confirmation=data.get("pending_confirmation", False),
            message_count=data.get("message_count", 0),
            handoff_context=data.get("handoff_context"),
        )


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
