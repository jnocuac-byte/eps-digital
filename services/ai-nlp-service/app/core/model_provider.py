from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from .logger import log_event


def _build_provider_pool() -> dict[str, RoutingCandidate]:
    """Construye el pool completo de providers disponibles (según API keys configuradas).

    Returns:
        Diccionario {nombre: RoutingCandidate} con todos los providers válidos.
    """
    from strands.models.routing.router import RoutingCandidate

    load_dotenv()
    pool: dict[str, RoutingCandidate] = {}

    # Groq — compatible con OpenAI API
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        from strands.models.openai import OpenAIModel

        pool["groq"] = RoutingCandidate(
            model=OpenAIModel(
                client_args={
                    "api_key": groq_key,
                    "base_url": "https://api.groq.com/openai/v1",
                },
                model_id="openai/gpt-oss-120b",
            ),
            name="groq",
        )

    # Gemini — múltiples keys para rotación automática (rate limit distribuido)
    try:
        from strands.models.gemini import GeminiModel

        gemini_registered = False
        for i in range(1, 4):
            key = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
            if key:
                name = f"gemini-{i}"
                pool[name] = RoutingCandidate(
                    model=GeminiModel(
                        client_args={"api_key": key},
                        model_id="gemini-3.6-flash",
                    ),
                    name=name,
                )
                gemini_registered = True

        # Fallback: si no hay keys numeradas, usar GEMINI_API_KEY como gemini-1
        if not gemini_registered:
            fallback_key = os.getenv("GEMINI_API_KEY", "").strip()
            if fallback_key:
                pool["gemini-1"] = RoutingCandidate(
                    model=GeminiModel(
                        client_args={"api_key": fallback_key},
                        model_id="gemini-3.6-flash",
                    ),
                    name="gemini-1",
                )
    except ImportError:
        log_event("MODEL", "INIT", "warning", "Gemini omitido: strands-agents[gemini] no instalado")

    # Cerebras — compatible con OpenAI API
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        from strands.models.openai import OpenAIModel

        pool["cerebras"] = RoutingCandidate(
            model=OpenAIModel(
                client_args={
                    "api_key": cerebras_key,
                    "base_url": "https://api.cerebras.ai/v1",
                },
                model_id="gpt-oss-120b",
            ),
            name="cerebras",
        )

    # Mistral — compatible con OpenAI API
    mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        from strands.models.openai import OpenAIModel

        pool["mistral"] = RoutingCandidate(
            model=OpenAIModel(
                client_args={
                    "api_key": mistral_key,
                    "base_url": "https://api.mistral.ai/v1",
                },
                model_id="mistral-small-latest",
            ),
            name="mistral",
        )

    return pool


def build_fallback_model(order: list[str] | None = None) -> Any:
    """Construye un ModelRouter de Strands con fallback multi-provider.

    Args:
        order: Lista de nombres de providers en orden de prioridad.
               Ej: ["mistral", "gemini", "cerebras", "groq"].
               Si es None, usa el orden por defecto del pool.

    Returns:
        ModelRouter listo para pasar a Agent(model=...).
    """
    from strands.models.routing.router import ModelRouter
    from strands.models.routing.fallback_strategy import FallbackStrategy

    pool = _build_provider_pool()

    if not pool:
        raise ValueError(
            "No hay proveedores LLM configurados. "
            "Configura al menos GROQ_API_KEY o GEMINI_API_KEY."
        )

    # Construir lista de candidates según el orden pedido
    if order:
        candidates = [pool[name] for name in order if name in pool]
        if not candidates:
            log_event(
                "MODEL", "INIT", "warning",
                f"Ningun provider del orden pedido ({order}) esta configurado. "
                f"Usando providers disponibles: {list(pool.keys())}"
            )
            candidates = list(pool.values())
    else:
        candidates = list(pool.values())

    router = ModelRouter(
        candidates,
        strategy=FallbackStrategy(),
    )

    log_event(
        "MODEL", "INIT", "info",
        f"ModelRouter creado con {len(candidates)} providers: "
        f"{[c.name for c in router.candidates]}"
    )

    return router
