from __future__ import annotations

from strands import Agent
from strands.event_loop._retry import ModelRetryStrategy

from .scheduling.prompt import SCHEDULING_SYSTEM_PROMPT
from .tools import SCHEDULING_TOOLS


def build_scheduling_agent(model: object) -> Agent:
    """Construye el agente de agendamiento con tools nativas.

    El agente ejecuta automáticamente las tools en secuencia:
    obtener_especialidades → obtener_medicos → agendar_cita.
    Strands maneja el loop de tool calling internamente.

    Args:
        model: ModelRouter o Model de Strands con fallback configurado.

    Returns:
        Agent de Strands configurado para agendamiento.
    """
    return Agent(
        name="scheduling_agent",
        system_prompt=SCHEDULING_SYSTEM_PROMPT,
        tools=SCHEDULING_TOOLS,
        model=model,
        callback_handler=None,
        retry_strategy=ModelRetryStrategy(max_attempts=1),
    )
