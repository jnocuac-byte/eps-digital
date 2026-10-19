"""Ingesta de la knowledge base de triaje a la tabla knowledge_chunks (H-18).

Uso (desde services/ai-nlp-service/):
    uv run python scripts/ingest_knowledge.py --dry-run   # solo imprime fragmentos
    uv run python scripts/ingest_knowledge.py             # recarga completa (borra + inserta)
    uv run python scripts/ingest_knowledge.py --append    # inserta sin borrar existentes
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from app.core.embeddings import get_gemini_embedding  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.knowledge import load_triage_guide  # noqa: E402
from app.models import KnowledgeChunk  # noqa: E402

TIPO_ESPECIALIDAD = "especialidad"
TIPO_URGENCIA = "nivel_urgencia"
TIPO_BANDERAS = "banderas_rojas_globales"


def build_chunks(guide: dict) -> list[tuple[str, str, str]]:
    """Construye los 12 fragmentos semanticos: 8 especialidades, 3 urgencias, 1 global.

    Returns:
        Lista de tuplas (tipo, nombre, contenido).
    """
    chunks: list[tuple[str, str, str]] = []

    # 1) Especialidades medicas (8)
    for esp in guide["especialidades_catalogo"]:
        lineas = [
            f"Especialidad: {esp['nombre']}",
            f"Descripcion: {esp['descripcion']}",
            "Sintomas comunes: " + "; ".join(esp["ejemplos_sintomas"]) + ".",
            f"Criterio de derivacion: {esp['criterio_derivacion']}",
        ]
        if esp.get("red_flags"):
            lineas.append("Banderas rojas: " + "; ".join(esp["red_flags"]))
        chunks.append((TIPO_ESPECIALIDAD, esp["nombre"], "\n".join(lineas)))

    # 2) Niveles de urgencia del protocolo de triaje (3)
    for clave, nivel in guide["protocolo_triaje"]["niveles_urgencia"].items():
        nombre = f"{clave.capitalize()} - Nivel {nivel['nivel']}"
        contenido = (
            f"Nivel {nivel['nivel']} ({clave}): {nivel['descripcion']} "
            f"Accion: {nivel['accion_inmediata']}. "
            f"Tiempo de respuesta: {nivel['tiempo_respuesta']}."
        )
        chunks.append((TIPO_URGENCIA, nombre, contenido))

    # 3) Banderas rojas globales (1) + mensaje de emergencia de reglas_negocio
    criterios = guide["criterios_banderas_rojas"]
    mensaje = guide.get("reglas_negocio", {}).get("mensaje_emergencia", "")
    lineas = [f"{i}. {criterio}" for i, criterio in enumerate(criterios, start=1)]
    if mensaje:
        lineas.append(mensaje)
    chunks.append((TIPO_BANDERAS, "Banderas rojas globales", "\n".join(lineas)))

    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta de knowledge base al vector store.")
    parser.add_argument("--dry-run", action="store_true", help="Imprime fragmentos sin tocar API ni BD.")
    parser.add_argument("--append", action="store_true", help="No borra knowledge_chunks existentes.")
    args = parser.parse_args()

    guide = load_triage_guide()
    chunks = build_chunks(guide)

    por_tipo: dict[str, int] = {}
    for tipo, _, _ in chunks:
        por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

    print(f"Fragmentos generados: {len(chunks)}")
    for tipo, cantidad in por_tipo.items():
        print(f"  - {tipo}: {cantidad}")

    if args.dry_run:
        print("\n--- DRY RUN: contenido de los fragmentos ---")
        for i, (tipo, nombre, contenido) in enumerate(chunks, start=1):
            print(f"\n[{i:02d}] ({tipo}) {nombre} ({len(contenido)} chars)")
            print(contenido)
        print("\nDry run finalizado: no se llamo a Gemini ni a la base de datos.")
        return

    db = SessionLocal()
    try:
        if not args.append:
            borrados = db.query(KnowledgeChunk).delete()
            print(f"knowledge_chunks existentes eliminados: {borrados}")

        for i, (tipo, nombre, contenido) in enumerate(chunks, start=1):
            embedding = get_gemini_embedding(contenido, task_type="RETRIEVAL_DOCUMENT")
            db.add(
                KnowledgeChunk(
                    tipo=tipo,
                    nombre=nombre,
                    contenido=contenido,
                    embedding=embedding,
                )
            )
            print(f"[{i:02d}/{len(chunks)}] embedding ok -> ({tipo}) {nombre}")

        db.commit()
        print(f"\nIngesta completada: {len(chunks)} filas en knowledge_chunks.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
