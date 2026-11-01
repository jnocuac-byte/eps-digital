from __future__ import annotations

import os
import re
from typing import Any, Iterable

from dotenv import load_dotenv

from .logger import log_event


GEMINI_MODEL_ID = "gemini-3.6-flash"
DEFAULT_GEMINI_LITE_MODEL_ID = "gemini-3.5-flash-lite"

# Patrones EXACTOS de nombres de candidatos por grupo. No usar startswith("gemini-"):
# casaría también con "gemini-lite-1" y int("lite-1") lanzaría ValueError.
_GEMINI_GROUP_PATTERN = re.compile(r"^gemini-(\d+)$")
_GEMINI_LITE_GROUP_PATTERN = re.compile(r"^gemini-lite-(\d+)$")


def _expand_group_names(pool_names: Iterable[str], order: list[str]) -> list[str]:
    """Expande los grupos "gemini" y "gemini-lite" a nombres exactos del pool.

    El grupo "gemini" toma solo los nombres ^gemini-\\d+$ y "gemini-lite" solo los
    ^gemini-lite-\\d+$, ambos ordenados por n. Los demás entries se copian tal cual
    si existen en el pool. Se eliminan duplicados preservando el orden.

    Args:
        pool_names: Nombres disponibles en el pool.
        order: Orden deseado, con grupos ("gemini", "gemini-lite") y/o nombres exactos.

    Returns:
        Lista de nombres expandidos y deduplicados.
    """
    available = list(pool_names)
    expanded: list[str] = []
    for entry in order:
        if entry == "gemini":
            pattern = _GEMINI_GROUP_PATTERN
        elif entry == "gemini-lite":
            pattern = _GEMINI_LITE_GROUP_PATTERN
        else:
            if entry in available:
                expanded.append(entry)
            continue
        matched = sorted(
            (int(match.group(1)), name)
            for name in available
            if (match := pattern.match(name))
        )
        expanded.extend(name for _, name in matched)

    seen: set[str] = set()
    ordered_names: list[str] = []
    for name in expanded:
        if name not in seen:
            seen.add(name)
            ordered_names.append(name)
    return ordered_names


def _build_provider_pool() -> dict[str, RoutingCandidate]:
    """Construye el pool completo de providers disponibles (según API keys configuradas).

    Cada GEMINI_API_KEY_n registra dos candidatos: "gemini-n" (gemini-3.6-flash) y
    "gemini-lite-n" (modelo de GEMINI_LITE_MODEL, por defecto gemini-3.5-flash-lite),
    ambos con la misma key. Si una key no existe, tampoco se registra su candidato lite.

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

    # Gemini — múltiples keys para rotación automática (rate limit distribuido).
    # Cada key n registra gemini-n (flash completo) y gemini-lite-n (flash-lite),
    # que tiene su propia cuota diaria por modelo.
    try:
        from strands.models.gemini import GeminiModel

        lite_model_id = (
            os.getenv("GEMINI_LITE_MODEL", "").strip() or DEFAULT_GEMINI_LITE_MODEL_ID
        )

        def _register_gemini_candidates(index: int, key: str) -> None:
            pool[f"gemini-{index}"] = RoutingCandidate(
                model=GeminiModel(
                    client_args={"api_key": key},
                    model_id=GEMINI_MODEL_ID,
                ),
                name=f"gemini-{index}",
            )
            pool[f"gemini-lite-{index}"] = RoutingCandidate(
                model=GeminiModel(
                    client_args={"api_key": key},
                    model_id=lite_model_id,
                ),
                name=f"gemini-lite-{index}",
            )

        gemini_registered = False
        i = 1
        while True:
            key = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
            if not key:
                break
            _register_gemini_candidates(i, key)
            gemini_registered = True
            i += 1

        # Fallback: si no hay keys numeradas, usar GEMINI_API_KEY como gemini-1
        if not gemini_registered:
            fallback_key = os.getenv("GEMINI_API_KEY", "").strip()
            if fallback_key:
                _register_gemini_candidates(1, fallback_key)
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

    # Expandir los grupos "gemini" y "gemini-lite" dinámicamente con patrones exactos
    # (^gemini-\d+$ y ^gemini-lite-\d+$); no fijar GEMINI_API_KEY_n aquí.
    if order:
        ordered_names = _expand_group_names(pool.keys(), order)
        candidates = [pool[name] for name in ordered_names]
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
