from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app import crud


class _ScalarResult:
	def __init__(self, values):
		self._values = values

	def all(self):
		return self._values


class _FakeDb:
	def __init__(self, citas):
		self._citas = citas

	def scalars(self, _statement):
		return _ScalarResult(self._citas)


@pytest.fixture
def slot_context(monkeypatch):
	fecha = date(2030, 1, 7)
	medico_a = uuid4()
	medico_b = uuid4()
	sede_a = uuid4()
	sede_b = uuid4()
	especialidad = uuid4()
	monkeypatch.setattr(crud, "hoy_bogota", lambda: date(2030, 1, 1))
	monkeypatch.setattr(
		crud,
		"_resolver_medicos_candidatos",
		lambda _fecha, _medico_id, _servicio_id, _especialidad_id: [medico_a, medico_b],
	)
	monkeypatch.setattr(
		crud,
		"_obtener_duracion_especialidad",
		lambda _especialidad_id: 40,
	)
	monkeypatch.setattr(
		crud,
		"_obtener_disponibilidades_medico",
		lambda medico, _dia: [
			{
				"especialidad_id": str(especialidad),
				"sede_id": str(sede_a if medico == medico_a else sede_b),
				"hora_inicio": "08:00:00",
				"hora_fin": "09:20:00",
				"activo": True,
			}
		],
	)
	return fecha, medico_a, medico_b, sede_a, sede_b, especialidad


def test_legacy_contract_deduplicates_by_hour(slot_context):
	fecha, *_ = slot_context
	slots = crud.generar_slots_disponibles(
		_FakeDb([]),
		fecha=fecha,
		especialidad_id=slot_context[-1],
	)

	assert slots == [
		{"hora_inicio": "08:00", "hora_fin": "08:40"},
		{"hora_inicio": "08:40", "hora_fin": "09:20"},
	]


def test_detailed_contract_preserves_combinations_and_duration(slot_context):
	fecha, medico_a, medico_b, sede_a, sede_b, especialidad = slot_context
	slots = crud.generar_slots_detallados(
		_FakeDb([]),
		fecha=fecha,
		especialidad_id=especialidad,
	)

	assert len(slots) == 4
	assert {slot["medico_id"] for slot in slots} == {str(medico_a), str(medico_b)}
	assert {slot["sede_id"] for slot in slots} == {str(sede_a), str(sede_b)}
	assert {slot["especialidad_id"] for slot in slots} == {str(especialidad)}
	assert {slot["hora_fin"] for slot in slots} == {"08:40", "09:20"}


def test_detailed_contract_excludes_occupied_slot(slot_context):
	fecha, medico_a, medico_b, _sede_a, _sede_b, especialidad = slot_context
	occupied = SimpleNamespace(
		medico_id=medico_a,
		fecha_cita=fecha,
		estado="programada",
		hora_inicio=time(8, 0),
		hora_fin=time(8, 40),
	)
	slots = crud.generar_slots_detallados(
		_FakeDb([occupied]),
		fecha=fecha,
		especialidad_id=especialidad,
	)

	assert len(slots) == 3
	assert not any(
		slot["medico_id"] == str(medico_a) and slot["hora_inicio"] == "08:00"
		for slot in slots
	)
	assert any(slot["medico_id"] == str(medico_b) and slot["hora_inicio"] == "08:00" for slot in slots)
