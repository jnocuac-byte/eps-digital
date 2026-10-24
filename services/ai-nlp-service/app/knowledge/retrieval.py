from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..core.embeddings import get_gemini_embedding
from ..core.logger import log_event
from ..models import KnowledgeChunk

DEFAULT_RAG_CLINICAL_SIMILARITY_THRESHOLD = 0.70
MAX_RAG_RESULTS = 3


@dataclass(frozen=True)
class RetrievedKnowledge:
    """Fragmento recuperado y su score de similitud semántica."""

    tipo: str
    nombre: str | None
    contenido: str
    similitud: float


def _similarity_threshold() -> float:
    """Lee el umbral RAG y conserva un valor seguro si está mal configurado."""
    raw_threshold = os.getenv("RAG_CLINICAL_SIMILARITY_THRESHOLD", "").strip()
    if not raw_threshold:
        return DEFAULT_RAG_CLINICAL_SIMILARITY_THRESHOLD

    try:
        threshold = float(raw_threshold)
    except ValueError:
        log_event(
            "RAG",
            "CONFIG",
            "warning",
            "Umbral RAG invalido; usando 0.70.",
        )
        return DEFAULT_RAG_CLINICAL_SIMILARITY_THRESHOLD

    if not 0.0 <= threshold <= 1.0:
        log_event(
            "RAG",
            "CONFIG",
            "warning",
            "Umbral RAG fuera de rango; usando 0.70.",
        )
        return DEFAULT_RAG_CLINICAL_SIMILARITY_THRESHOLD
    return threshold


def retrieve_knowledge(
    db: Session,
    query: str,
    *,
    limit: int = MAX_RAG_RESULTS,
) -> list[RetrievedKnowledge]:
    """Recupera los fragmentos médicos más similares para una consulta.

    La recuperación es best effort: un fallo de embeddings o de la consulta
    vectorial no interrumpe el flujo conversacional.
    """
    if not query or not query.strip():
        return []

    result_limit = max(1, min(limit, MAX_RAG_RESULTS))
    threshold = _similarity_threshold()

    try:
        query_vector = get_gemini_embedding(
            query,
            task_type="RETRIEVAL_QUERY",
        )
        distance = KnowledgeChunk.embedding.cosine_distance(query_vector)
        rows = (
            db.query(
                KnowledgeChunk.tipo,
                KnowledgeChunk.nombre,
                KnowledgeChunk.contenido,
                distance.label("distancia"),
            )
            .order_by(distance)
            .limit(result_limit)
            .all()
        )

        results: list[RetrievedKnowledge] = []
        for row in rows:
            similarity = 1.0 - float(row.distancia)
            if similarity >= threshold:
                results.append(
                    RetrievedKnowledge(
                        tipo=row.tipo,
                        nombre=row.nombre,
                        contenido=row.contenido,
                        similitud=round(similarity, 6),
                    )
                )

        best_similarity = results[0].similitud if results else None
        log_event(
            "RAG",
            "SEARCH",
            "debug",
            f"Resultados={len(results)} mejor_similitud={best_similarity}",
        )
        return results
    except Exception as exc:
        log_event(
            "RAG",
            "SEARCH",
            "warning",
            f"Busqueda semantica omitida: {type(exc).__name__}: {exc}",
        )
        return []
