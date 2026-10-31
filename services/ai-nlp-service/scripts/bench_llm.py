"""Benchmark aislado del turno de selección de hora del scheduling agent.

No modifica el ModelRouter ni realiza llamadas HTTP a los servicios locales.
Cada ejecución usa una tool falsa para evitar crear drafts o citas reales.
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from strands import Agent, tool
from strands.hooks.events import AfterModelCallEvent, BeforeModelCallEvent

from app.agents.scheduling.prompt import SCHEDULING_SYSTEM_PROMPT
from app.core.model_provider import _build_provider_pool


OPTIONS_JSON = {
    "ok": True,
    "fecha": "2026-11-02",
    "opciones": [
        {
            "hora_inicio": "07:00",
            "hora_fin": "07:20",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
        {
            "hora_inicio": "07:20",
            "hora_fin": "07:40",
            "medico_id": "fa111111-1111-4111-a111-111111111111",
            "sede_id": "b1111111-1111-4111-b111-111111111111",
        },
    ],
    "mensaje": "Encontré disponibilidad para el 2026-11-02.",
}


@tool
def proponer_cita(
    fecha: str,
    hora: str,
    sede: str = "",
    elegir_automaticamente: bool = False,
) -> dict[str, Any]:
    """Tool falsa: devuelve el JSON de opciones sin crear una reserva real."""
    return OPTIONS_JSON


@dataclass
class Measurement:
    provider: str
    configuration: str
    repetition: int
    status: str
    total_ms: int
    model_calls: int
    model_call_ms: list[int]
    error: str = ""


def _benchmark_prompt() -> str:
    return (
        f"{SCHEDULING_SYSTEM_PROMPT}\n\n"
        "## CONTEXTO DEL BENCHMARK\n"
        "specialty_id: e1111111-1111-4111-a111-111111111111\n"
        "Especialidad identificada: Medicina General\n"
        "El turno anterior ofreció estas opciones: 07:00, 07:20.\n"
        "para esta medición, usa proponer_cita como la herramienta disponible "
        "para seleccionar la opción exacta elegida por el paciente."
    )


def _message() -> str:
    return (
        "## HISTORIAL\n"
        "Asistente: Encontré disponibilidad para el lunes 2 de noviembre de 2026: "
        "07:00 y 07:20.\n\n"
        "## MENSAJE DEL PACIENTE\n"
        "Me parece bien 7:20"
    )


def _attach_timing(agent: Agent, timings: list[int]) -> None:
    starts: list[float] = []

    def before(event: BeforeModelCallEvent) -> None:
        starts.append(time.perf_counter())

    def after(event: AfterModelCallEvent) -> None:
        if starts:
            timings.append(round((time.perf_counter() - starts.pop()) * 1000))

    agent.hooks.add_callback(BeforeModelCallEvent, before, order=40)
    agent.hooks.add_callback(AfterModelCallEvent, after, order=60)


def _make_gemini_variants() -> list[tuple[str, Any]]:
    from strands.models.gemini import GeminiModel

    key = os.getenv("GEMINI_API_KEY_1", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return []

    return [
        (
            "gemini-current",
            GeminiModel(
                client_args={"api_key": key},
                model_id=os.getenv("BENCH_GEMINI_MODEL", "gemini-3.6-flash"),
            ),
        ),
        (
            "gemini-thinking-0",
            GeminiModel(
                client_args={"api_key": key},
                model_id=os.getenv("BENCH_GEMINI_MODEL", "gemini-3.6-flash"),
                params={"thinking_config": {"thinking_budget": 0}},
            ),
        ),
        (
            "gemini-lite",
            GeminiModel(
                client_args={"api_key": key},
                model_id=os.getenv("BENCH_GEMINI_LITE_MODEL", "gemini-3.5-flash-lite"),
            ),
        ),
    ]


def _run_one(provider: str, configuration: str, model: Any, repetition: int) -> Measurement:
    timings: list[int] = []
    agent = Agent(
        name="bench_scheduling_agent",
        system_prompt=_benchmark_prompt(),
        tools=[proponer_cita],
        model=model,
        callback_handler=None,
        retry_strategy=None,
    )
    _attach_timing(agent, timings)
    started = time.perf_counter()
    try:
        agent(_message())
        return Measurement(
            provider=provider,
            configuration=configuration,
            repetition=repetition,
            status="ok",
            total_ms=round((time.perf_counter() - started) * 1000),
            model_calls=len(timings),
            model_call_ms=timings,
        )
    except Exception as exc:
        return Measurement(
            provider=provider,
            configuration=configuration,
            repetition=repetition,
            status="error",
            total_ms=round((time.perf_counter() - started) * 1000),
            model_calls=len(timings),
            model_call_ms=timings,
            error=f"{type(exc).__name__}: {exc}",
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=1, choices=range(1, 4))
    args = parser.parse_args()
    load_dotenv()

    configurations: list[tuple[str, str, Any]] = []
    for provider, candidate in _build_provider_pool().items():
        configurations.append((provider, "router-default", candidate.model))
    configurations.extend(
        ("gemini-1", name, model) for name, model in _make_gemini_variants()
    )

    if not configurations:
        raise SystemExit("No hay proveedores configurados.")

    results: list[Measurement] = []
    for provider, configuration, model in configurations:
        for repetition in range(1, args.repetitions + 1):
            results.append(_run_one(provider, configuration, model, repetition))

    print("provider | configuration | rep | status | total_ms | model_calls | call_ms | error")
    print("-" * 110)
    for result in results:
        print(
            f"{result.provider} | {result.configuration} | {result.repetition} | "
            f"{result.status} | {result.total_ms} | {result.model_calls} | "
            f"{','.join(map(str, result.model_call_ms)) or '-'} | {result.error}"
        )
    print()
    print(f"Configuraciones: {len(configurations)}")
    print(f"Repeticiones por configuración: {args.repetitions}")
    print(f"Peticiones LLM consumidas: {sum(item.model_calls for item in results)}")


if __name__ == "__main__":
    main()
