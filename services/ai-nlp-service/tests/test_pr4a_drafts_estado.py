"""PR4 pasos 1-2: ConversationState con drafts de cancelar/reagendar y TurnContext.

Sin BD ni LLM: modulos puros (conversation_state / turn_context).
"""

from app.core.conversation_state import (
	BookingDraft,
	CancelDraft,
	ConversationState,
	RescheduleDraft,
)
from app.core.turn_context import TurnContext


def _booking_draft() -> BookingDraft:
	return BookingDraft(
		usuario_id="u1",
		especialidad_id="e1",
		especialidad_nombre="Medicina General",
		medico_id="m1",
		medico_nombre="Dra. Perez",
		sede_id="s1",
		sede_nombre="Sede Norte",
		sede_direccion="Calle 1",
		tipo_servicio="medicina_general",
		fecha="2026-11-02",
		hora_inicio="08:00",
		hora_fin="08:30",
	)


def _cancel_draft() -> CancelDraft:
	return CancelDraft(
		cita_id="cita-1",
		usuario_id="u1",
		fecha="2026-11-02",
		hora_inicio="08:00",
		hora_fin="08:30",
		medico_id="m1",
		medico_nombre="Dra. Perez",
		sede_id="s1",
		sede_nombre="Sede Norte",
		especialidad_nombre="Medicina General",
	)


def _reschedule_draft() -> RescheduleDraft:
	return RescheduleDraft(
		cita_id="cita-1",
		usuario_id="u1",
		fecha_original="2026-11-02",
		hora_inicio_original="08:00",
		hora_fin_original="08:30",
		medico_id="m1",
		medico_nombre="Dra. Perez",
		sede_id="s1",
		sede_nombre="Sede Norte",
		especialidad_nombre="Medicina General",
		nueva_fecha="2026-11-05",
		nueva_hora_inicio="10:00",
		nueva_hora_fin="10:30",
	)


def _contexto(state: ConversationState) -> TurnContext:
	return TurnContext(conversation_id="conv-1", usuario_id="u1", state=state)


# --- Paso 1: compatibilidad con estados persistidos (sin migracion Alembic) ---


def test_estado_viejo_sin_campos_nuevos_se_rehidrata():
	estado_viejo = {
		"active_agent": "scheduling",
		"pending_action": "agendar",
		"booking_draft": _booking_draft().to_dict(),
		"last_booking_id": "abc",
		"last_booking_summary": "resumen",
		"message_count": 4,
	}
	state = ConversationState.from_dict(estado_viejo)
	assert state.pending_action == "agendar"
	assert state.booking_draft is not None
	assert state.cancel_draft is None
	assert state.reschedule_draft is None
	assert state.last_booking_id == "abc"
	assert state.message_count == 4


def test_from_dict_minimo_no_revienta():
	state = ConversationState.from_dict({})
	assert state.pending_action is None
	assert state.booking_draft is None
	assert state.cancel_draft is None
	assert state.reschedule_draft is None
	assert state.message_count == 0


def test_roundtrip_cancel_draft():
	state = ConversationState(
		pending_action="cancelar", cancel_draft=_cancel_draft()
	)
	rehidratada = ConversationState.from_dict(state.to_dict())
	assert rehidratada.pending_action == "cancelar"
	assert rehidratada.cancel_draft == _cancel_draft()
	assert rehidratada.booking_draft is None


def test_roundtrip_reschedule_draft_conserva_originales():
	state = ConversationState(
		pending_action="reagendar", reschedule_draft=_reschedule_draft()
	)
	rehidratada = ConversationState.from_dict(state.to_dict())
	assert rehidratada.pending_action == "reagendar"
	assert rehidratada.reschedule_draft == _reschedule_draft()
	assert rehidratada.reschedule_draft.fecha_original == "2026-11-02"
	assert rehidratada.reschedule_draft.nueva_fecha == "2026-11-05"


# --- Paso 2: TurnContext ---


def test_set_draft_por_defecto_sigue_siendo_agendar():
	# Compatibilidad: proponer_cita llama set_draft(draft) sin action.
	state = ConversationState()
	ctx = _contexto(state)
	ctx.set_draft(_booking_draft())
	assert state.pending_action == "agendar"
	assert state.booking_draft == _booking_draft()


def test_set_draft_cancelar_reemplaza_draft_de_agendar():
	state = ConversationState(
		pending_action="agendar", booking_draft=_booking_draft()
	)
	ctx = _contexto(state)
	ctx.set_draft(_cancel_draft(), action="cancelar")
	assert state.pending_action == "cancelar"
	assert state.cancel_draft == _cancel_draft()
	# Un solo draft activo: el de agendar quedo limpio (caso l).
	assert state.booking_draft is None
	assert state.reschedule_draft is None


def test_set_draft_reagendar_reemplaza_draft_anterior():
	state = ConversationState(pending_action="cancelar", cancel_draft=_cancel_draft())
	ctx = _contexto(state)
	ctx.set_draft(_reschedule_draft(), action="reagendar")
	assert state.pending_action == "reagendar"
	assert state.reschedule_draft == _reschedule_draft()
	assert state.cancel_draft is None


def test_set_draft_limpia_idempotencia_previa():
	state = ConversationState(
		last_booking_id="abc", last_booking_summary="resumen previo"
	)
	ctx = _contexto(state)
	ctx.set_draft(_cancel_draft(), action="cancelar")
	assert state.last_booking_id is None
	assert state.last_booking_summary is None
	assert state.pending_confirmation is True


def test_rollback_restaura_draft_de_agendar_tras_fallo():
	state = ConversationState(
		pending_action="agendar", booking_draft=_booking_draft()
	)
	ctx = _contexto(state)
	ctx.set_draft(_cancel_draft(), action="cancelar")
	ctx.rollback()
	assert state.pending_action == "agendar"
	assert state.booking_draft == _booking_draft()
	assert state.cancel_draft is None


def test_rollback_sin_draft_previo_limpia_todo():
	state = ConversationState()
	ctx = _contexto(state)
	ctx.set_draft(_reschedule_draft(), action="reagendar")
	ctx.rollback()
	assert state.pending_action is None
	assert state.reschedule_draft is None
	assert state.booking_draft is None
	assert state.pending_confirmation is False


def test_rollback_restaura_idempotencia():
	state = ConversationState(
		last_booking_id="abc", last_booking_summary="resumen"
	)
	ctx = _contexto(state)
	ctx.set_draft(_cancel_draft(), action="cancelar")
	ctx.rollback()
	assert state.last_booking_id == "abc"
	assert state.last_booking_summary == "resumen"


# --- Correcciones: snapshot al inicio del turno y sanitizado de pending_action ---


def test_rollback_sin_set_draft_conserva_el_draft_del_inicio():
	# Un fallo ajeno a set_draft no debe borrar una propuesta pendiente valida.
	state = ConversationState(
		pending_action="cancelar",
		cancel_draft=_cancel_draft(),
		pending_confirmation=True,
	)
	ctx = _contexto(state)
	ctx.rollback()
	assert state.pending_action == "cancelar"
	assert state.cancel_draft == _cancel_draft()
	assert state.pending_confirmation is True


def test_doble_set_draft_en_un_turno_y_rollback_va_al_inicio():
	# set_draft(agendar) y luego set_draft(cancelar) en el MISMO turno:
	# el rollback debe restaurar el estado del inicio del turno, no el intermedio.
	state = ConversationState(
		pending_action="reagendar",
		reschedule_draft=_reschedule_draft(),
		pending_confirmation=True,
	)
	ctx = _contexto(state)
	ctx.set_draft(_booking_draft())            # intermedio (agendar)
	ctx.set_draft(_cancel_draft(), action="cancelar")  # intermedio (cancelar)
	ctx.rollback()
	assert state.pending_action == "reagendar"
	assert state.reschedule_draft == _reschedule_draft()
	assert state.booking_draft is None
	assert state.cancel_draft is None
	assert state.pending_confirmation is True


def test_from_dict_con_pending_action_invalido_se_trata_como_none():
	state = ConversationState.from_dict(
		{"pending_action": "borrar", "message_count": 2}
	)
	assert state.pending_action is None
	assert state.message_count == 2
