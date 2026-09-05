from __future__ import annotations

from strands import Agent

from .triage.prompt import TRIAGE_SYSTEM_PROMPT
from .triage.models.output import TriageAnalysis


def build_triage_agent(model: object) -> Agent:
    """Construye el agente de triaje con structured output.

    El agente retorna un TriageAnalysis estructurado directamente,
    sin necesidad de parsing regex de bloques [CLASIFICACION].

    Args:
        model: ModelRouter o Model de Strands con fallback configurado.

    Returns:
        Agent de Strands configurado para triaje.
    """
    return Agent(
        name="triage_agent",
        system_prompt=TRIAGE_SYSTEM_PROMPT,
        structured_output_model=TriageAnalysis,
        model=model,
        tools=[],
        callback_handler=None,
        retry_strategy=None,
    )
