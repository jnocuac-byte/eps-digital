from __future__ import annotations

from strands import Agent

from .scheduling.prompt import SCHEDULING_SYSTEM_PROMPT
from .tools import SCHEDULING_TOOLS


def build_scheduling_agent(model: object) -> Agent:
    """Construye el agente de agendamiento con tools nativas.

    El agente ejecuta automáticamente las tools necesarias para el flujo,
    comenzando con un specialty_id UUID entregado por el orquestador.
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
        retry_strategy=None,
    )
