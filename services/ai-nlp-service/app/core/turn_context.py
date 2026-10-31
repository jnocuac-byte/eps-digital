from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from copy import deepcopy
from .conversation_state import (
    BookingDraft,
    CancelDraft,
    ConversationState,
    RescheduleDraft,
)

PendingAction = Literal["agendar", "cancelar", "reagendar"]

_DRAFTS_BY_ACTION = {
    "agendar": "booking_draft",
    "cancelar": "cancel_draft",
    "reagendar": "reschedule_draft",
}


@dataclass
class TurnContext:
    """Contexto mutable y transaccional de un turno del scheduling agent.

    El snapshot del estado se toma al CREAR el contexto (__post_init__):
    rollback() siempre restaura el estado del inicio del turno, aunque
    set_draft no se haya llamado, se haya llamado dos veces, o el fallo
    sea ajeno a la creacion de un draft.
    """

    conversation_id: str
    usuario_id: str | None
    state: ConversationState
    _previous_draft: BookingDraft | CancelDraft | RescheduleDraft | None = field(init=False, default=None)
    _previous_pending_action: PendingAction | None = field(init=False, default=None)
    _previous_pending_confirmation: bool = field(init=False, default=False)
    _previous_last_booking_id: str | None = field(init=False, default=None)
    _previous_last_booking_summary: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._previous_draft = deepcopy(self._draft_activo())
        self._previous_pending_action = self.state.pending_action
        self._previous_pending_confirmation = self.state.pending_confirmation
        self._previous_last_booking_id = self.state.last_booking_id
        self._previous_last_booking_summary = self.state.last_booking_summary

    def set_draft(
        self,
        draft: BookingDraft | CancelDraft | RescheduleDraft,
        action: PendingAction = "agendar",
    ) -> None:
        """Guarda el draft de la accion indicada; permite rollback al estado inicial.

        Un solo draft activo a la vez: el nuevo reemplaza a los otros dos.
        """
        for attr in _DRAFTS_BY_ACTION.values():
            setattr(self.state, attr, None)
        setattr(self.state, _DRAFTS_BY_ACTION[action], draft)
        self.state.pending_action = action
        self.state.pending_confirmation = True
        self.state.last_booking_id = None
        self.state.last_booking_summary = None

    def rollback(self) -> None:
        """Restaura el estado tal como estaba al inicio del turno."""
        for attr in _DRAFTS_BY_ACTION.values():
            setattr(self.state, attr, None)
        if self._previous_draft is not None:
            setattr(
                self.state,
                _DRAFTS_BY_ACTION[self._previous_pending_action or "agendar"],
                self._previous_draft,
            )
        self.state.pending_action = self._previous_pending_action
        self.state.pending_confirmation = self._previous_pending_confirmation
        self.state.last_booking_id = self._previous_last_booking_id
        self.state.last_booking_summary = self._previous_last_booking_summary

    def _draft_activo(self) -> BookingDraft | CancelDraft | RescheduleDraft | None:
        if self.state.pending_action == "cancelar":
            return self.state.cancel_draft
        if self.state.pending_action == "reagendar":
            return self.state.reschedule_draft
        return self.state.booking_draft
