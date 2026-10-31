"""Replay manual de propuesta, confirmacion y autorizacion explicita.

Uso:
    cd services/ai-nlp-service
    CATALOG_SERVICE_URL=http://localhost:8004 \
    CITAS_SERVICE_URL=http://localhost:8003 \
    PYTHONPATH=. uv run python scripts/replay_scheduling_loop.py
"""

from __future__ import annotations

import asyncio
import argparse
import re
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from app.agents import tools
from app.agents.scheduling_agent import build_scheduling_agent
from app.agents.triage_agent import build_triage_agent
from app.core.model_provider import build_fallback_model
from app.core.orchestrator import Orchestrator
from app.database import SessionLocal
from app.crud import crear_conversacion


class CountingAgent:
    """Proxy que cuenta invocaciones LLM sin cambiar el agente Strands."""

    def __init__(self, agent):
        self._agent = agent
        self.calls = 0

    @property
    def messages(self):
        return self._agent.messages

    @messages.setter
    def messages(self, value):
        self._agent.messages = value

    @property
    def hooks(self):
        return self._agent.hooks

    @property
    def _provider_used(self):
        return getattr(self._agent, "_provider_used", "unknown")

    @_provider_used.setter
    def _provider_used(self, value):
        self._agent._provider_used = value

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self._agent(*args, **kwargs)


class CountingClient:
    def __init__(self, original, counters, created_ids=None):
        self._client = original
        self._counters = counters
        self._created_ids = created_ids

    def __enter__(self):
        self._client.__enter__()
        return self

    def __exit__(self, *args):
        return self._client.__exit__(*args)

    def get(self, url, **kwargs):
        self._counters.append(("GET", url))
        return self._client.get(url, **kwargs)

    def post(self, url, **kwargs):
        self._counters.append(("POST", url))
        response = self._client.post(url, **kwargs)
        if (
            self._created_ids is not None
            and url.rstrip("/").endswith("/citas")
            and 200 <= response.status_code < 300
        ):
            try:
                cita_id = response.json().get("cita_id")
                if cita_id:
                    self._created_ids.append(str(cita_id))
            except ValueError:
                pass
        return response


class StubSchedulingAgent:
    """Agente guionado: selecciona un horario sin invocar ningún LLM."""

    def __init__(self):
        self.messages = []
        self.hooks = type("Hooks", (), {"add_callback": lambda *_args, **_kwargs: None})()
        self._provider_used = "stub"
        self.calls = 0

    def __call__(self, message, **kwargs):
        self.calls += 1
        patient_message = message.rsplit("## MENSAJE DEL PACIENTE", 1)[-1]
        match = re.search(r"\b(\d{1,2}:\d{2})\b", patient_message)
        if match:
            date_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", patient_message)
            fecha = date_match.group(1) if date_match else "2026-11-02"
            invocation_state = kwargs["invocation_state"]
            context = type(
                "ToolContext",
                (),
                {"invocation_state": invocation_state},
            )()
            result = tools.proponer_cita(
                fecha,
                match.group(1),
                elegir_automaticamente=True,
                tool_context=context,
            )
            return f"Modo stub: {result}"
        return "Modo stub: sin hora; respuesta fija."


async def run_scenario(name: str, messages: list[str]) -> None:
    http_calls: list[tuple[str, str]] = []
    original_client = tools.httpx.Client
    tools._CATALOG_CACHE.clear()
    try:
        triage = CountingAgent(
            build_triage_agent(
                build_fallback_model(
                    order=["gemini", "groq", "cerebras", "mistral"]
                )
            )
        )
        scheduling = CountingAgent(
            build_scheduling_agent(
                build_fallback_model(
                    order=["gemini", "groq", "cerebras", "mistral"]
                )
            )
        )
        tools.httpx.Client = lambda **kwargs: CountingClient(
            original_client(**kwargs), http_calls
        )
        orchestrator = Orchestrator(triage, scheduling)
        conversation_id = str(uuid4())
        usuario_id = str(uuid4())
        history: list[dict[str, str]] = []
        print(f"\n=== {name} ===")

        for turn, message in enumerate(messages, start=1):
            before_http = len(http_calls)
            before_llm = triage.calls + scheduling.calls
            response, state = await orchestrator.process(
                conversation_id,
                message,
                history,
                usuario_id=usuario_id,
            )
            turn_http = http_calls[before_http:]
            turn_llm = triage.calls + scheduling.calls - before_llm
            print(f"\nTURN {turn}: {message}")
            print(f"LLM calls: {turn_llm}")
            print(f"HTTP calls: {turn_http or 'none'}")
            print(response)
            print(
                f"pending_action={state.pending_action}, "
                f"draft={'yes' if state.booking_draft else 'no'}, "
                f"last_booking={'yes' if state.last_booking_id else 'no'}"
            )
            history.extend(
                [
                    {"role": "user", "content": message},
                    {"role": "assistant", "content": response},
                ]
            )
    finally:
        tools.httpx.Client = original_client


def _stub_state(orchestrator, conversation_id, usuario_id):
    state = orchestrator.get_state(conversation_id)
    state.active_agent = "scheduling"
    state.specialty_id = "e1111111-1111-4111-a111-111111111111"
    state.specialty_name = "Consulta Medicina General"
    state.symptoms_summary = "Fiebre y dolor de garganta"
    return state


def _print_stub_turn(turn, message, response, state, http_calls, before_http):
    print(f"\nTURN {turn}: {message}")
    print("LLM calls: 0")
    print(f"HTTP calls: {http_calls[before_http:] or 'none'}")
    print(response)
    print(
        f"pending_action={state.pending_action}, "
        f"draft={'yes' if state.booking_draft else 'no'}, "
        f"last_booking={'yes' if state.last_booking_id else 'no'}"
    )


def _available_stub_times(client, citas_url: str, fecha: str) -> list[str]:
    response = client.get(
        f"{citas_url}/citas/slots-detallados",
        params={
            "especialidad_id": "e1111111-1111-4111-a111-111111111111",
            "fecha": fecha,
        },
    )
    if not 200 <= response.status_code < 300:
        return []
    return [
        str(slot.get("hora_inicio", ""))[:5]
        for slot in response.json()
        if slot.get("hora_inicio")
    ]


async def run_stub() -> None:
    http_calls: list[tuple[str, str]] = []
    created_ids: list[str] = []
    cancelled_ids: list[str] = []
    original_client = tools.httpx.Client
    tools._CATALOG_CACHE.clear()
    db = SessionLocal()
    usuario_id = uuid4()
    try:
        tools.httpx.Client = lambda **kwargs: CountingClient(
            original_client(**kwargs), http_calls, created_ids
        )
        citas_url = tools._obtener_citas_service_url()
        if not citas_url:
            raise RuntimeError("CITAS_SERVICE_URL no configurado.")
        with original_client(timeout=tools.CITAS_TIMEOUT_SECONDS) as client:
            available_times = _available_stub_times(client, citas_url, "2026-11-02")
        if len(available_times) < 3:
            print(
                "STUB omitido: se requieren al menos 3 slots disponibles el "
                f"2026-11-02 y solo hay {len(available_times)}."
            )
            return
        proposal_time, ambiguous_time, restart_time = available_times[:3]

        def new_conversation():
            conversation = crear_conversacion(db, usuario_id)
            return str(conversation.conversacion_id)

        async def process(orchestrator, conversation_id, message, history):
            before_http = len(http_calls)
            response, state = await orchestrator.process(
                conversation_id, message, history, usuario_id=str(usuario_id), db=db
            )
            _print_stub_turn(
                len(history) // 2 + 1,
                message,
                response,
                state,
                http_calls,
                before_http,
            )
            history.extend(
                [{"role": "user", "content": message}, {"role": "assistant", "content": response}]
            )
            return state

        print("\n=== stub: propuesta, confirmacion, doble confirmacion ===")
        conversation_id = new_conversation()
        orchestrator = Orchestrator(StubSchedulingAgent(), StubSchedulingAgent())
        _stub_state(orchestrator, conversation_id, str(usuario_id))
        orchestrator._persist_state(conversation_id, orchestrator.get_state(conversation_id), db)
        history: list[dict[str, str]] = []
        await process(orchestrator, conversation_id, f"2026-11-02 a las {proposal_time}", history)
        await process(orchestrator, conversation_id, "Sí confirmo", history)
        await process(orchestrator, conversation_id, "Sí", history)

        print("\n=== stub: ambiguo y negacion ===")
        conversation_id = new_conversation()
        orchestrator = Orchestrator(StubSchedulingAgent(), StubSchedulingAgent())
        _stub_state(orchestrator, conversation_id, str(usuario_id))
        orchestrator._persist_state(conversation_id, orchestrator.get_state(conversation_id), db)
        history = []
        await process(orchestrator, conversation_id, f"2026-11-02 a las {ambiguous_time}", history)
        await process(orchestrator, conversation_id, "sí pero a las 8", history)
        await process(orchestrator, conversation_id, "no", history)

        print("\n=== stub: reinicio y confirmacion desde BD ===")
        conversation_id = new_conversation()
        first = Orchestrator(StubSchedulingAgent(), StubSchedulingAgent())
        _stub_state(first, conversation_id, str(usuario_id))
        first._persist_state(conversation_id, first.get_state(conversation_id), db)
        history = []
        await process(first, conversation_id, f"2026-11-02 a las {restart_time}", history)
        restarted = Orchestrator(StubSchedulingAgent(), StubSchedulingAgent())
        await process(restarted, conversation_id, "confirmo", history)

        print("\n=== stub: cupo ocupado ===")
        conversation_id = new_conversation()
        occupied = Orchestrator(StubSchedulingAgent(), StubSchedulingAgent())
        _stub_state(occupied, conversation_id, str(usuario_id))
        occupied._persist_state(conversation_id, occupied.get_state(conversation_id), db)
        await process(occupied, conversation_id, f"2026-11-02 a las {proposal_time}", [])
        if citas_url:
            with original_client(timeout=tools.CITAS_TIMEOUT_SECONDS) as client:
                for cita_id in created_ids:
                    response = client.post(
                        f"{citas_url}/citas/{cita_id}/cancelar",
                        json={"motivo": "Replay --stub"},
                        headers={"Content-Type": "application/json", "X-User-ID": str(usuario_id)},
                    )
                    if 200 <= response.status_code < 300:
                        cancelled_ids.append(cita_id)
        print(f"\nSTUB cleanup: created_cita_ids={created_ids}")
        print(f"STUB cleanup: cancelled_cita_ids={cancelled_ids}")
    finally:
        tools.httpx.Client = original_client
        db.close()


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stub", action="store_true", help="Ejecuta replay sin LLM.")
    args = parser.parse_args()
    if args.stub:
        await run_stub()
        return
    await run_scenario(
        "confirmacion en turno siguiente",
        [
            "Tengo fiebre y dolor de garganta",
            "Agéndame una cita",
            "Para el 2026-11-02 a las 07:40",
            "SI CONFIRMO",
        ],
    )
    await run_scenario(
        "autorizacion explicita en el mismo turno",
        [
            "Tengo fiebre y dolor de garganta",
            "Para el 2026-11-02 a las 07:40, decide tú y agéndala",
        ],
    )


if __name__ == "__main__":
    asyncio.run(main())
