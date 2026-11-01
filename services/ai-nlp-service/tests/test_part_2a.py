from uuid import uuid4

import pytest

from app.agents import tools
from app.agents.scheduling.prompt import SCHEDULING_SYSTEM_PROMPT
from app.core.conversation_state import ConversationState
from app.core.orchestrator import Orchestrator


class _FakeAgent:
	def __init__(self, response=None, tool_call=None):
		self.messages = []
		self._provider_used = "fake"
		self._response = response
		self._tool_call = tool_call
		self.hooks = _FakeHooks()

	def __call__(self, _message):
		if self._tool_call:
			self._tool_call()
		return self._response or "respuesta de prueba"


class _FakeHooks:
	def add_callback(self, *_args, **_kwargs):
		return None


class _FakeStructuredResponse:
	def __init__(self, output):
		self.output = output


@pytest.fixture(autouse=True)
def clear_catalog_cache():
	tools._CATALOG_CACHE.clear()
	yield
	tools._CATALOG_CACHE.clear()


def test_catalog_cache_reuses_specialties_sites_and_doctors(monkeypatch):
	calls = []

	def fake_catalog(endpoint, params=None):
		calls.append((endpoint, params))
		return {"ok": True, "data": [{"endpoint": endpoint}]}

	monkeypatch.setattr(tools, "_consultar_catalog_service", fake_catalog)

	tools.obtener_especialidades()
	tools.obtener_especialidades()
	tools.obtener_sedes()
	tools.obtener_sedes()
	tools.obtener_medicos("specialty-1")
	tools.obtener_medicos("specialty-1")
	tools.obtener_medicos("specialty-2")

	assert calls == [
		("/especialidades", None),
		("/sedes", None),
		("/especialidades/specialty-1/medicos", None),
		("/especialidades/specialty-2/medicos", None),
	]


def test_catalog_cache_does_not_store_failed_responses(monkeypatch):
	calls = []
	responses = [
		{"ok": False, "error": "timeout"},
		{"ok": True, "data": [{"especialidad_id": str(uuid4())}]},
	]

	def fake_catalog(endpoint, params=None):
		calls.append(endpoint)
		return responses.pop(0)

	monkeypatch.setattr(tools, "_consultar_catalog_service", fake_catalog)

	first = tools._consultar_catalog_service_cached("/especialidades")
	second = tools._consultar_catalog_service_cached("/especialidades")

	assert first["ok"] is False
	assert second["ok"] is True
	assert calls == ["/especialidades", "/especialidades"]


def test_scheduling_fake_agent_does_not_repeat_catalog_http(monkeypatch):
	specialty_id = str(uuid4())
	calls = []

	def fake_catalog(endpoint, params=None):
		calls.append(endpoint)
		return {"ok": True, "data": []}

	monkeypatch.setattr(tools, "_consultar_catalog_service", fake_catalog)

	def fixed_tool_calls():
		tools.obtener_medicos(specialty_id)
		tools.obtener_medicos(specialty_id)

	orchestrator = Orchestrator(
		_FakeAgent(response={"output": {"explicacion_al_paciente": "triage"}}),
		_FakeAgent(tool_call=fixed_tool_calls),
	)
	state = orchestrator.get_state("conversation-1")
	state.active_agent = "scheduling"
	state.specialty_id = specialty_id
	state.specialty_name = "Medicina General"

	import asyncio

	response, _ = asyncio.run(
		orchestrator.process(
			"conversation-1",
			"Muéstrame horarios",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert response == "respuesta de prueba"
	assert calls == [f"/especialidades/{specialty_id}/medicos"]


def test_invalid_specialty_never_reaches_scheduling_agent():
	scheduling_called = False

	def mark_called():
		nonlocal scheduling_called
		scheduling_called = True

	orchestrator = Orchestrator(
		_FakeAgent(),
		_FakeAgent(tool_call=mark_called),
	)
	state = orchestrator.get_state("conversation-2")
	state.active_agent = "scheduling"
	state.specialty_id = None

	import asyncio

	response, updated_state = asyncio.run(
		orchestrator.process(
			"conversation-2",
			"Quiero agendar una cita",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert "sintomas" in response
	assert updated_state.active_agent == "triage"
	assert scheduling_called is False


def test_direct_specialty_name_resolves_without_scheduling_llm(monkeypatch):
	specialty_id = str(uuid4())
	monkeypatch.setattr(
		tools,
		"_consultar_catalog_service",
		lambda endpoint, params=None: {
			"ok": True,
			"data": [{"especialidad_id": specialty_id, "nombre": "Cardiología"}],
		},
	)
	scheduling_called = False

	def mark_called():
		nonlocal scheduling_called
		scheduling_called = True

	orchestrator = Orchestrator(_FakeAgent(), _FakeAgent(tool_call=mark_called))
	state = orchestrator.get_state("conversation-specialty")

	import asyncio

	_, updated_state = asyncio.run(
		orchestrator.process(
			"conversation-specialty",
			"Quiero cita de cardiología",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert updated_state.specialty_id == specialty_id
	assert scheduling_called is True


def test_real_catalog_names_resolve_service_name_without_llm(monkeypatch):
	specialty_id = str(uuid4())

	def fake_catalog(endpoint, params=None):
		if endpoint == "/especialidades":
			return {
				"ok": True,
				"data": [{
					"especialidad_id": specialty_id,
					"nombre": "Consulta Medicina General",
					"servicio_id": "servicio-general",
				}],
			}
		return {
			"ok": True,
			"data": [{"servicio_id": "servicio-general", "nombre": "Medicina General"}],
		}

	monkeypatch.setattr(tools, "_consultar_catalog_service", fake_catalog)
	orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())

	import asyncio

	_, updated_state = asyncio.run(
		orchestrator.process(
			"conversation-real-name",
			"Quiero una cita de medicina general",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert updated_state.specialty_id == specialty_id


def test_message_without_specialty_clue_returns_direct_prompt():
	orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
	state = orchestrator.get_state("conversation-no-clue")

	import asyncio

	response, updated_state = asyncio.run(
		orchestrator.process(
			"conversation-no-clue",
			"Quiero agendar una cita",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert response == (
		"Para ayudarte a agendar necesito conocer primero tus sintomas "
		"o la especialidad que necesitas."
	)
	assert updated_state.active_agent == "triage"


def test_ambiguous_specialty_name_returns_direct_prompt(monkeypatch):
	monkeypatch.setattr(
		tools,
		"_consultar_catalog_service",
		lambda endpoint, params=None: {
			"ok": True,
			"data": [
				{"especialidad_id": str(uuid4()), "nombre": "Medicina General"},
				{"especialidad_id": str(uuid4()), "nombre": "Medicina Interna"},
			],
		},
	)
	orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())

	import asyncio

	response, updated_state = asyncio.run(
		orchestrator.process(
			"conversation-ambiguous",
			"Quiero agendar medicina general o medicina interna",
			[],
			usuario_id=str(uuid4()),
		)
	)

	assert response == (
		"Para ayudarte a agendar necesito conocer primero tus sintomas "
		"o la especialidad que necesitas."
	)
	assert updated_state.active_agent == "triage"


def test_triage_persists_resolved_uuid_and_handoff_context(monkeypatch):
	resolved_id = str(uuid4())
	classification = {
		"especialidad_sugerida_id": "medicina_general",
		"especialidad_sugerida_nombre": "Medicina General",
		"resumen_clinico": "Fiebre",
		"nivel_urgencia": "programable",
		"red_flag": {"detected": False},
	}

	async def resolve_slug(_slug, _name):
		return resolved_id

	triage_agent = _FakeAgent(response=_FakeStructuredResponse(classification))
	orchestrator = Orchestrator(triage_agent, _FakeAgent())
	monkeypatch.setattr(orchestrator, "_resolver_slug", resolve_slug)
	state = ConversationState()

	import asyncio

	asyncio.run(
		orchestrator._process_triage(
			"conversation-3", "Tengo fiebre", [], None, state
		)
	)

	assert state.specialty_id == resolved_id
	assert state.handoff_context["specialty_id"] == resolved_id


def test_context_is_built_once_and_prompt_has_no_runtime_placeholders():
	state = ConversationState(
		specialty_id=str(uuid4()),
		specialty_name="Medicina General",
		symptoms_summary="Fiebre",
	)
	orchestrator = Orchestrator(_FakeAgent(), _FakeAgent())
	context = orchestrator._build_system_context(state, "user-1")

	assert "Fecha actual del sistema:" in context
	assert "usuario_id del paciente: user-1" in context
	assert state.specialty_id in context
	assert "Sintomas reportados: Fiebre" in context
	assert "{contexto_paciente}" not in SCHEDULING_SYSTEM_PROMPT
	assert "{fecha_actual}" not in SCHEDULING_SYSTEM_PROMPT
	assert tools.obtener_especialidades not in __import__(
		"app.agents.tools", fromlist=["SCHEDULING_TOOLS"]
	).SCHEDULING_TOOLS
	assert tools.obtener_sedes in __import__(
		"app.agents.tools", fromlist=["SCHEDULING_TOOLS"]
	).SCHEDULING_TOOLS


def test_prompt_and_toolset_have_same_tool_names():
	import re

	toolset = {
		tool.__name__
		for tool in __import__("app.agents.tools", fromlist=["SCHEDULING_TOOLS"]).SCHEDULING_TOOLS
	}
	prompt_tools = set(
		re.findall(r"^- ([a-z_]+)\(", SCHEDULING_SYSTEM_PROMPT, re.MULTILINE)
	)

	assert prompt_tools == toolset


def test_search_options_uses_one_appointments_request_and_resolves_names(monkeypatch):
	specialty_id = str(uuid4())
	medico_id = str(uuid4())
	sede_id = str(uuid4())
	requests = []

	class _Response:
		status_code = 200

		def json(self):
			return {
				"fecha": "2026-11-02",
				"opciones": [{
					"medico_id": medico_id,
					"sede_id": sede_id,
					"especialidad_id": specialty_id,
					"hora_inicio": "07:00",
					"hora_fin": "07:20",
				}],
			}

	class _Client:
		def __enter__(self):
			return self

		def __exit__(self, *_args):
			return None

		def get(self, url, **kwargs):
			requests.append((url, kwargs))
			return _Response()

	monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
	def fake_cached_catalog(endpoint):
		if endpoint == "/sedes":
			return {
				"ok": True,
				"data": [{"sede_id": sede_id, "nombre": "Sede Central", "direccion": "Calle 1"}],
			}
		return {
			"ok": True,
			"data": {"medico_id": medico_id, "nombres": "Ana", "apellidos": "Gómez"},
		}

	monkeypatch.setattr(tools, "_consultar_catalog_service_cached", fake_cached_catalog)
	monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")

	import json

	result = json.loads(tools.buscar_opciones_cita(specialty_id))

	assert len(requests) == 1
	assert "/citas/proxima-disponibilidad" in requests[0][0]
	assert result["fecha"] == "2026-11-02"
	assert result["opciones"][0]["medico_nombre"] == "Ana Gómez"
	assert result["opciones"][0]["sede_nombre"] == "Sede Central"


def test_search_options_network_failure_returns_error(monkeypatch):
	class _Client:
		def __enter__(self):
			return self

		def __exit__(self, *_args):
			return None

		def get(self, *_args, **_kwargs):
			raise tools.httpx.RequestError("offline")

	monkeypatch.setattr(tools.httpx, "Client", lambda **_kwargs: _Client())
	monkeypatch.setattr(tools, "_obtener_citas_service_url", lambda: "http://citas")

	import json

	result = json.loads(tools.buscar_opciones_cita(str(uuid4())))

	assert result["ok"] is False
