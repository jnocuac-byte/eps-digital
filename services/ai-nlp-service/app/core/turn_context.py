from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
from .conversation_state import BookingDraft, ConversationState


@dataclass
class TurnContext:
    """Contexto mutable y transaccional de un turno del scheduling agent."""

    conversation_id: str
    usuario_id: str | None
    state: ConversationState
    _previous_draft: BookingDraft | None = None
    _previous_last_booking_id: str | None = None
    _previous_last_booking_summary: str | None = None

    def set_draft(self, draft: BookingDraft) -> None:
        """Guarda el draft y permite restaurarlo si el turno falla."""
        self._previous_draft = deepcopy(self.state.booking_draft)
        self._previous_last_booking_id = self.state.last_booking_id
        self._previous_last_booking_summary = self.state.last_booking_summary
        self.state.booking_draft = draft
        self.state.pending_action = "agendar"
        self.state.pending_confirmation = True
        self.state.last_booking_id = None
        self.state.last_booking_summary = None

    def rollback(self) -> None:
        """Restaura el draft que existía antes de invocar al agente."""
        self.state.booking_draft = self._previous_draft
        self.state.pending_action = "agendar" if self._previous_draft else None
        self.state.pending_confirmation = bool(self._previous_draft)
        self.state.last_booking_id = self._previous_last_booking_id
        self.state.last_booking_summary = self._previous_last_booking_summary
