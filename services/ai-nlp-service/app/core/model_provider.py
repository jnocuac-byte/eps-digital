from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from .logger import log_event


def build_fallback_model() -> Any:
    """Construye un ModelRouter de Strands con fallback multi-provider.

    Orden de prioridad: Groq → Gemini → Cerebras → Mistral.
    El FallbackStrategy de Strands intenta el primer provider y pasa al
    siguiente si falla (429/5xx/timeout), reordenando automáticamente
    por tasa de fallo.

    Returns:
        ModelRouter listo para pasar a Agent(model=...).
    """
    from strands.models.routing.router import ModelRouter
    from strands.models.routing.fallback_strategy import FallbackStrategy

    load_dotenv()
    candidates: list[Any] = []

    # 1. Groq (primario) — compatible con OpenAI API
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        from strands.models.openai import OpenAIModel

        candidates.append(
            OpenAIModel(
                client_args={
                    "api_key": groq_key,
                    "base_url": "https://api.groq.com/openai/v1",
                },
                model_id="openai/gpt-oss-120b",
            )
        )
        log_event("MODEL", "INIT", "info", "Groq provider registrado (openai/gpt-oss-120b)")

    # 2. Gemini (secundario)
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        from strands.models.gemini import GoogleModel

        candidates.append(
            GoogleModel(
                model_id="gemini-3.6-flash",
                api_key=gemini_key,
            )
        )
        log_event("MODEL", "INIT", "info", "Gemini provider registrado (gemini-3.6-flash)")

    # 3. Cerebras (terciario) — compatible con OpenAI API
    cerebras_key = os.getenv("CEREBRAS_API_KEY", "").strip()
    if cerebras_key:
        from strands.models.openai import OpenAIModel

        candidates.append(
            OpenAIModel(
                client_args={
                    "api_key": cerebras_key,
                    "base_url": "https://api.cerebras.ai/v1",
                },
                model_id="gpt-oss-120b",
            )
        )
        log_event("MODEL", "INIT", "info", "Cerebras provider registrado (gpt-oss-120b)")

    # 4. Mistral (cuaternario) — compatible con OpenAI API
    mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if mistral_key:
        from strands.models.openai import OpenAIModel

        candidates.append(
            OpenAIModel(
                client_args={
                    "api_key": mistral_key,
                    "base_url": "https://api.mistral.ai/v1",
                },
                model_id="mistral-small-latest",
            )
        )
        log_event("MODEL", "INIT", "info", "Mistral provider registrado (mistral-small-latest)")

    if not candidates:
        raise ValueError(
            "No hay proveedores LLM configurados. "
            "Configura al menos GROQ_API_KEY o GEMINI_API_KEY."
        )

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
