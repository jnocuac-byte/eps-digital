from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import Literal

_UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def es_uuid_valido(valor: str) -> bool:
    """Retorna True si el valor es un UUID v4 válido (formato PostgreSQL)."""
    return bool(_UUID_REGEX.match(valor))

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

    # Contexto legado del agendamiento (se conserva para rehidratar estados viejos).
    selected_doctor_id: str | None = None
    selected_doctor_name: str | None = None
    selected_sede_id: str | None = None
    selected_sede_name: str | None = None
    selected_date: str | None = None
    selected_time: str | None = None
    pending_confirmation: bool = False

    pending_action: Literal["agendar"] | None = None
    booking_draft: BookingDraft | None = None
    last_booking_id: str | None = None
    last_booking_summary: str | None = None
    execution_started_at: str | None = None
    draft_shown_message_count: int | None = None
    draft_expires_at: str | None = None
    last_options_message_count: int | None = None

    # Metadata
    message_count: int = 0
    handoff_context: dict | None = None

    def to_dict(self) -> dict:
        """Serializa el estado a un diccionario JSON-compatible."""
        data = asdict(self)
        if self.booking_draft is not None:
            data["booking_draft"] = self.booking_draft.to_dict()
        return data

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
            pending_action=data.get("pending_action"),
            booking_draft=BookingDraft.from_dict(data["booking_draft"]) if data.get("booking_draft") else None,
            last_booking_id=data.get("last_booking_id"),
            last_booking_summary=data.get("last_booking_summary"),
            execution_started_at=data.get("execution_started_at"),
            draft_shown_message_count=data.get("draft_shown_message_count"),
            draft_expires_at=data.get("draft_expires_at"),
            last_options_message_count=data.get("last_options_message_count"),
            message_count=data.get("message_count", 0),
            handoff_context=data.get("handoff_context"),
        )


@dataclass
class BookingDraft:
    """Datos completos y verificables de una reserva pendiente."""

    usuario_id: str
    especialidad_id: str
    especialidad_nombre: str
    medico_id: str
    medico_nombre: str
    sede_id: str
    sede_nombre: str
    sede_direccion: str
    tipo_servicio: str
    fecha: str
    hora_inicio: str
    hora_fin: str
    descripcion_sintomas: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BookingDraft":
        return cls(
            usuario_id=str(data.get("usuario_id", "")),
            especialidad_id=str(data.get("especialidad_id", "")),
            especialidad_nombre=str(data.get("especialidad_nombre", "")),
            medico_id=str(data.get("medico_id", "")),
            medico_nombre=str(data.get("medico_nombre", "")),
            sede_id=str(data.get("sede_id", "")),
            sede_nombre=str(data.get("sede_nombre", "")),
            sede_direccion=str(data.get("sede_direccion", "")),
            tipo_servicio=str(data.get("tipo_servicio", "")),
            fecha=str(data.get("fecha", "")),
            hora_inicio=str(data.get("hora_inicio", "")),
            hora_fin=str(data.get("hora_fin", "")),
            descripcion_sintomas=str(data.get("descripcion_sintomas", "")),
        )

    def is_complete(self) -> bool:
        return all(
            (
                self.usuario_id,
                self.especialidad_id,
                self.medico_id,
                self.sede_id,
                self.tipo_servicio,
                self.fecha,
                self.hora_inicio,
                self.hora_fin,
            )
        )


def classify_intent(
    message: str, state: ConversationState, semantic_clinical: bool = False
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

    # Palabras clave médicas o similitud semántica → triage
    if semantic_clinical or any(kw in msg for kw in TRIAGE_KEYWORDS):
        return "triage"

    # Sin señal clara → continuar con agente actual
    if state.active_agent != "idle":
        return "continue"

    # Default: triage (primera interacción más común)
    return "triage"
