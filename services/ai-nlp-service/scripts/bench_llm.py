"""Benchmark aislado del scheduling agent con verificación de tools falsas.

Dos escenarios (sin llamadas HTTP a servicios locales, sin crear drafts ni citas reales):

- ``seleccion``: el paciente elige "7:20" tras ver 07:00 y 07:20. Se verifica que el
  modelo llame a ``proponer_cita`` UNA sola vez con fecha ``2026-11-02`` y hora ``07:20``
  (columna ``tool_ok``; los argumentos que recibe la tool falsa se registran en cada run).
- ``agenda``: el paciente solo dice "Agéndame una cita". Se verifica que llame a la tool
  falsa ``buscar_opciones_cita`` UNA sola vez.

Configuraciones permitidas: ``groq`` (openai/gpt-oss-120b) y ``gemini-lite``
(gemini-3.5-flash-lite). Los modelos Gemini completos quedan EXCLUIDOS (cuota agotada).

Uso:
    cd services/ai-nlp-service
    PYTHONPATH=. python scripts/bench_llm.py --turn seleccion --repetitions 3
    PYTHONPATH=. python scripts/bench_llm.py --turn agenda --repetitions 3
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from dotenv import load_dotenv
from strands import Agent, tool
from strands.hooks.events import AfterModelCallEvent, BeforeModelCallEvent

from app.agents.scheduling.prompt import SCHEDULING_SYSTEM_PROMPT


SELECCION_FECHA = "2026-11-02"
SELECCION_HORA = "07:20"

OPTIONS_JSON = {
    "ok": True,
    "fecha": SELECCION_FECHA,
    "opciones": [
        {
            "hora_inicio": "07:00",
            "hora_fin": "07:20",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
        {
            "hora_inicio": SELECCION_HORA,
            "hora_fin": "07:40",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
    ],
    "mensaje": f"Encontré disponibilidad para el {SELECCION_FECHA}.",
}

BUSCAR_JSON = {
    "ok": True,
    "fecha": "2026-11-05",
    "opciones": [
        {
            "hora_inicio": "08:00",
            "hora_fin": "08:20",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
        {
            "hora_inicio": "08:20",
            "hora_fin": "08:40",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
    ],
    "mensaje": "Encontré disponibilidad para el 2026-11-05.",
}


def _make_tools() -> tuple[list[Any], list[dict[str, Any]]]:
    """Crea las tools falsas y la lista que registra cada invocación con sus argumentos."""
    calls: list[dict[str, Any]] = []

    @tool
    def proponer_cita(
        fecha: str,
        hora: str,
        sede: str = "",
        elegir_automaticamente: bool = False,
    ) -> dict[str, Any]:
        """Tool falsa: devuelve el JSON de opciones sin crear una reserva real."""
        calls.append(
            {
                "tool": "proponer_cita",
                "fecha": fecha,
                "hora": hora,
                "sede": sede,
                "elegir_automaticamente": elegir_automaticamente,
            }
        )
        return OPTIONS_JSON

    @tool
    def buscar_opciones_cita(especialidad_id: str, fecha_desde: str = "") -> dict[str, Any]:
        """Tool falsa: devuelve opciones de la primera fecha disponible sin consultar servicios."""
        calls.append(
            {
                "tool": "buscar_opciones_cita",
                "especialidad_id": especialidad_id,
                "fecha_desde": fecha_desde,
            }
        )
        return BUSCAR_JSON

    return [proponer_cita, buscar_opciones_cita], calls


def _check_seleccion(calls: list[dict[str, Any]]) -> tuple[bool, str]:
    propuestas = [c for c in calls if c["tool"] == "proponer_cita"]
    if len(propuestas) != 1:
        return False, f"proponer_cita llamada {len(propuestas)} veces (se esperaba 1)"
    elegida = propuestas[0]
    if elegida["fecha"] != SELECCION_FECHA or elegida["hora"] != SELECCION_HORA:
        return False, f"argumentos inesperados: fecha={elegida['fecha']} hora={elegida['hora']}"
    return True, "proponer_cita(2026-11-02, 07:20) x1"


def _check_agenda(calls: list[dict[str, Any]]) -> tuple[bool, str]:
    busquedas = [c for c in calls if c["tool"] == "buscar_opciones_cita"]
    if len(busquedas) != 1:
        return False, f"buscar_opciones_cita llamada {len(busquedas)} veces (se esperaba 1)"
    return True, "buscar_opciones_cita x1"


@dataclass(frozen=True)
class Scenario:
    name: str
    system_prompt: str
    user_message: str
    check: Callable[[list[dict[str, Any]]], tuple[bool, str]]


def _selection_prompt() -> str:
    return (
        f"{SCHEDULING_SYSTEM_PROMPT}\n\n"
        "## CONTEXTO DEL BENCHMARK\n"
        f"specialty_id: e1111111-1111-4111-a111-111111111111\n"
        "Especialidad identificada: Medicina General\n"
        "usuario_id: 55555555-5555-4555-a555-555555555555\n"
        "El turno anterior ofreció estas opciones: 07:00, 07:20.\n"
        "para esta medición, usa proponer_cita como la herramienta disponible "
        "para seleccionar la opción exacta elegida por el paciente."
    )


def _selection_message() -> str:
    return (
        "## HISTORIAL\n"
        f"Asistente: Encontré disponibilidad para el lunes 2 de noviembre de 2026: "
        f"07:00 y {SELECCION_HORA}.\n\n"
        "## MENSAJE DEL PACIENTE\n"
        "Me parece bien 7:20"
    )


def _agenda_prompt() -> str:
    return (
        f"{SCHEDULING_SYSTEM_PROMPT}\n\n"
        "## CONTEXTO DEL BENCHMARK\n"
        "specialty_id: e1111111-1111-4111-a111-111111111111\n"
        "Especialidad identificada: Medicina General\n"
        "usuario_id: 55555555-5555-4555-a555-555555555555\n"
        "Fecha actual: 2026-10-31"
    )


def _agenda_message() -> str:
    return "## MENSAJE DEL PACIENTE\nAgéndame una cita"


SCENARIOS: dict[str, Scenario] = {
    "seleccion": Scenario(
        name="seleccion",
        system_prompt=_selection_prompt(),
        user_message=_selection_message(),
        check=_check_seleccion,
    ),
    "agenda": Scenario(
        name="agenda",
        system_prompt=_agenda_prompt(),
        user_message=_agenda_message(),
        check=_check_agenda,
    ),
}


@dataclass
class Measurement:
    provider: str
    scenario: str
    repetition: int
    status: str
    total_ms: int
    model_calls: int
    model_call_ms: list[int]
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_ok: bool = False
    tool_detail: str = ""
    error: str = ""


def _attach_timing(agent: Agent, timings: list[int]) -> None:
    starts: list[float] = []

    def before(event: BeforeModelCallEvent) -> None:
        starts.append(time.perf_counter())

    def after(event: AfterModelCallEvent) -> None:
        if starts:
            timings.append(round((time.perf_counter() - starts.pop()) * 1000))

    agent.hooks.add_callback(BeforeModelCallEvent, before, order=40)
    agent.hooks.add_callback(AfterModelCallEvent, after, order=60)


def _make_configurations() -> list[tuple[str, Any]]:
    """Solo groq y gemini-lite (gemini-3.5-flash-lite); sin modelos Gemini completos."""
    configurations: list[tuple[str, Any]] = []

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        from strands.models.openai import OpenAIModel

        configurations.append(
            (
                "groq",
                OpenAIModel(
                    client_args={
                        "api_key": groq_key,
                        "base_url": "https://api.groq.com/openai/v1",
                    },
                    model_id="openai/gpt-oss-120b",
                ),
            )
        )

    lite_key = (
        os.getenv("GEMINI_API_KEY_1", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    )
    if lite_key:
        from strands.models.gemini import GeminiModel

        configurations.append(
            (
                "gemini-lite",
                GeminiModel(
                    client_args={"api_key": lite_key},
                    model_id=os.getenv("BENCH_GEMINI_LITE_MODEL", "gemini-3.5-flash-lite"),
                ),
            )
        )

    return configurations


def _fmt_tool_calls(calls: list[dict[str, Any]]) -> str:
    if not calls:
        return "-"
    parts: list[str] = []
    for call in calls:
        args = ",".join(f"{k}={v}" for k, v in call.items() if k != "tool" and v not in ("", False))
        parts.append(f"{call['tool']}({args})")
    return "; ".join(parts)


def _run_one(provider: str, scenario: Scenario, model: Any, repetition: int) -> Measurement:
    timings: list[int] = []
    tools, calls = _make_tools()
    agent = Agent(
        name=f"bench_{scenario.name}_agent",
        system_prompt=scenario.system_prompt,
        tools=tools,
        model=model,
        callback_handler=None,
        retry_strategy=None,
    )
    _attach_timing(agent, timings)
    started = time.perf_counter()
    try:
        agent(scenario.user_message)
        tool_ok, tool_detail = scenario.check(calls)
        return Measurement(
            provider=provider,
            scenario=scenario.name,
            repetition=repetition,
            status="ok",
            total_ms=round((time.perf_counter() - started) * 1000),
            model_calls=len(timings),
            model_call_ms=timings,
            tool_calls=calls,
            tool_ok=tool_ok,
            tool_detail=tool_detail,
        )
    except Exception as exc:
        return Measurement(
            provider=provider,
            scenario=scenario.name,
            repetition=repetition,
            status="error",
            total_ms=round((time.perf_counter() - started) * 1000),
            model_calls=len(timings),
            model_call_ms=timings,
            tool_calls=calls,
            tool_ok=False,
            tool_detail="sin evaluar (excepción)",
            error=f"{type(exc).__name__}: {exc}",
        )


def _print_report(results: list[Measurement], repetitions: int) -> None:
    print("provider | scenario | rep | status | total_ms | model_calls | call_ms | tool_ok | tool_args | error")
    print("-" * 140)
    for r in results:
        print(
            f"{r.provider} | {r.scenario} | {r.repetition} | {r.status} | {r.total_ms} | "
            f"{r.model_calls} | {','.join(map(str, r.model_call_ms)) or '-'} | "
            f"{r.tool_ok} ({r.tool_detail}) | {_fmt_tool_calls(r.tool_calls)} | {r.error}"
        )
    print()

    groups: dict[tuple[str, str], list[Measurement]] = defaultdict(list)
    for r in results:
        groups[(r.provider, r.scenario)].append(r)

    print("provider | scenario | runs | tool_ok | mediana_ms | peor_ms | peticiones")
    print("-" * 80)
    for (provider, scenario), items in groups.items():
        oks = [item for item in items if item.status == "ok"]
        med = round(statistics.median(item.total_ms for item in oks)) if oks else "-"
        worst = max((item.total_ms for item in oks), default=None)
        requests = sum(item.model_calls for item in items)
        print(
            f"{provider} | {scenario} | {len(items)} | "
            f"{sum(1 for item in items if item.tool_ok)}/{len(items)} | "
            f"{med} | {worst if worst is not None else '-'} | {requests}"
        )
    print()

    print(f"Configuraciones: {len(_make_configurations())} (solo groq y gemini-lite)")
    print(f"Repeticiones por configuración/escenario: {repetitions}")
    print(f"Peticiones LLM consumidas (total): {sum(item.model_calls for item in results)}")
    by_provider: dict[str, int] = defaultdict(int)
    for item in results:
        by_provider[item.provider] += item.model_calls
    for provider, count in by_provider.items():
        print(f"  - {provider}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=3, choices=(1, 2, 3))
    parser.add_argument("--turn", choices=("seleccion", "agenda", "ambos"), default="ambos")
    args = parser.parse_args()
    load_dotenv()

    configurations = _make_configurations()
    if not configurations:
        raise SystemExit("No hay proveedores configurados (falta GROQ_API_KEY o GEMINI_API_KEY_1).")

    scenario_names = ("seleccion", "agenda") if args.turn == "ambos" else (args.turn,)

    results: list[Measurement] = []
    for scenario_name in scenario_names:
        scenario = SCENARIOS[scenario_name]
        for provider, model in configurations:
            for repetition in range(1, args.repetitions + 1):
                results.append(_run_one(provider, scenario, model, repetition))

    _print_report(results, args.repetitions)


if __name__ == "__main__":
    main()
