"""Cliente de embeddings de Gemini para la base de conocimiento vectorial (H-18)."""
from __future__ import annotations

import os
import time

from dotenv import load_dotenv


EMBEDDING_MODEL = "models/gemini-embedding-001"
EMBEDDING_DIM = 768

# Errores que no se reintentan (auth / permisos / peticion mal formada).
_FATAL_MARKERS = ("api key", "api_key", "permission_denied", "unauthorized", "invalid argument")


def _resolve_api_key() -> str:
    """Resuelve la API key de Gemini: GOOGLE_API_KEY -> GEMINI_API_KEY -> GEMINI_API_KEY_1..3."""
    load_dotenv()
    for name in ("GOOGLE_API_KEY", "GEMINI_API_KEY"):
        key = os.getenv(name, "").strip()
        if key:
            return key
    for i in range(1, 4):
        key = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if key:
            return key
    raise ValueError(
        "No hay API key de Gemini configurada "
        "(define GOOGLE_API_KEY, GEMINI_API_KEY o GEMINI_API_KEY_1..3)."
    )


def get_gemini_embedding(text: str, task_type: str, *, max_retries: int = 3) -> list[float]:
    """Genera un embedding de 768 dimensiones para `text` con gemini-embedding-001.

    Args:
        text: Texto a vectorizar.
        task_type: Tipo de tarea de embedding
            (RETRIEVAL_DOCUMENT en ingesta, RETRIEVAL_QUERY en busqueda).
        max_retries: Intentos totales ante errores transitorios (429/5xx).

    Returns:
        Lista de 768 floats.
    """
    import google.generativeai as genai

    if not text or not text.strip():
        raise ValueError("get_gemini_embedding: el texto no puede estar vacio.")

    api_key = _resolve_api_key()
    genai.configure(api_key=api_key)

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=text,
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIM,
            )
            embedding = result["embedding"]
            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding de dimension inesperada: {len(embedding)} != {EMBEDDING_DIM}."
                )
            return embedding
        except ValueError:
            raise
        except Exception as exc:  # noqa: BLE001 — el SDK expone excepciones heterogeneas
            last_error = exc
            message = str(exc).lower()
            if any(marker in message for marker in _FATAL_MARKERS):
                raise
            if attempt < max_retries - 1:
                delay = 2**attempt
                time.sleep(delay)

    raise RuntimeError(
        f"get_gemini_embedding fallo tras {max_retries} intentos: {last_error}"
    ) from last_error
