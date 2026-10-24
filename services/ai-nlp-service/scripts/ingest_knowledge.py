"""Ingesta idempotente de la knowledge base vectorial.

Uso (desde services/ai-nlp-service/):
    uv run python scripts/ingest_knowledge.py --dry-run
    uv run python scripts/ingest_knowledge.py
    uv run python scripts/ingest_knowledge.py --replace --delay-seconds 1
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))

from app.core.embeddings import EMBEDDING_DIM, get_gemini_embedding  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.knowledge import load_triage_guide  # noqa: E402
from app.knowledge.data.primary_care_catalog import (  # noqa: E402
    DATASET_VERSION,
    PRIMARY_CARE_CATALOG,
)
from app.models import KnowledgeChunk  # noqa: E402

TIPO_ESPECIALIDAD = "especialidad"
TIPO_URGENCIA = "nivel_urgencia"
TIPO_BANDERAS = "banderas_rojas_globales"
TIPO_CATALOGO = "catalogo_atencion_primaria"


def build_guide_chunks(guide: dict) -> list[tuple[str, str, str, str]]:
    """Construye fragmentos de la guía estática con claves estables."""
    chunks: list[tuple[str, str, str, str]] = []

    for esp in guide["especialidades_catalogo"]:
        lineas = [
            f"Especialidad: {esp['nombre']}",
            f"Descripcion: {esp['descripcion']}",
            "Sintomas comunes: " + "; ".join(esp["ejemplos_sintomas"]) + ".",
            f"Criterio de derivacion: {esp['criterio_derivacion']}",
        ]
        if esp.get("red_flags"):
            lineas.append("Banderas rojas: " + "; ".join(esp["red_flags"]))
        chunks.append(
            (
                TIPO_ESPECIALIDAD,
                esp["nombre"],
                "\n".join(lineas),
                f"guide:{TIPO_ESPECIALIDAD}:{esp['nombre']}",
            )
        )

    for clave, nivel in guide["protocolo_triaje"]["niveles_urgencia"].items():
        nombre = f"{clave.capitalize()} - Nivel {nivel['nivel']}"
        contenido = (
            f"Nivel {nivel['nivel']} ({clave}): {nivel['descripcion']} "
            f"Accion: {nivel['accion_inmediata']}. "
            f"Tiempo de respuesta: {nivel['tiempo_respuesta']}."
        )
        chunks.append(
            (TIPO_URGENCIA, nombre, contenido, f"guide:{TIPO_URGENCIA}:{nombre}")
        )

    criterios = guide["criterios_banderas_rojas"]
    mensaje = guide.get("reglas_negocio", {}).get("mensaje_emergencia", "")
    lineas = [f"{i}. {criterio}" for i, criterio in enumerate(criterios, start=1)]
    if mensaje:
        lineas.append(mensaje)
    chunks.append(
        (
            TIPO_BANDERAS,
            "Banderas rojas globales",
            "\n".join(lineas),
            f"guide:{TIPO_BANDERAS}:Banderas rojas globales",
        )
    )
    return chunks


def build_catalog_chunks(
    dataset_version: str = DATASET_VERSION,
) -> list[tuple[str, str, str, str]]:
    """Convierte el catálogo curado a texto enriquecido para embeddings."""
    chunks: list[tuple[str, str, str, str]] = []
    for entry in PRIMARY_CARE_CATALOG:
        fuente = entry["fuente"]
        referencia = entry["referencia"]
        codigo = entry["codigo_cie11"] or "No asignado: requiere verificación específica."
        contenido = "\n".join(
            [
                f"Especialidad: {entry['especialidad']}",
                f"Motivo de consulta: {entry['motivo_consulta']}",
                "Terminos frecuentes: " + "; ".join(entry["terminos"]) + ".",
                f"Diagnostico o sindrome orientativo: {entry['diagnostico_o_sindrome']}.",
                f"Nivel de urgencia sugerido: {entry['nivel_urgencia']}.",
                f"Criterios de derivacion: {entry['criterios_derivacion']}",
                "Banderas rojas: " + "; ".join(entry["banderas_rojas"]) + ".",
                f"Codigo CIE-11: {codigo}",
                f"Fuente: {fuente}. Referencia: {referencia}.",
                f"Version del dataset: {dataset_version}.",
            ]
        )
        chunks.append(
            (
                TIPO_CATALOGO,
                f"{entry['especialidad']} — {entry['motivo_consulta']}",
                contenido,
                f"catalog:{entry['id']}",
            )
        )
    return chunks


def build_chunks(
    guide: dict,
    *,
    dataset_version: str = DATASET_VERSION,
) -> list[tuple[str, str, str, str]]:
    """Combina guía general y catálogo enriquecido."""
    chunks = build_guide_chunks(guide)
    chunks.extend(build_catalog_chunks(dataset_version))
    source_keys = [source_key for _, _, _, source_key in chunks]
    if len(source_keys) != len(set(source_keys)):
        raise ValueError("El dataset contiene source_key duplicadas.")
    return chunks


def _validate_chunks(chunks: list[tuple[str, str, str, str]]) -> None:
    if not chunks:
        raise ValueError("No se generaron fragmentos para ingerir.")
    for tipo, nombre, contenido, source_key in chunks:
        if not all((tipo, nombre, contenido, source_key)):
            raise ValueError("Todos los fragmentos requieren tipo, nombre, contenido y source_key.")
        if len(source_key) > 255:
            raise ValueError(f"source_key demasiado larga: {source_key}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta de knowledge base al vector store.")
    parser.add_argument("--dry-run", action="store_true", help="No llama a Gemini ni toca la BD.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Compatibilidad: conserva filas no incluidas y hace upsert de las generadas.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Elimina filas fuera del dataset actual antes del upsert.",
    )
    parser.add_argument("--batch-size", type=int, default=10, help="Filas por commit.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.5,
        help="Pausa entre llamadas nuevas a Gemini.",
    )
    parser.add_argument(
        "--dataset-version",
        default=DATASET_VERSION,
        help="Versión que se escribe en el texto del catálogo.",
    )
    args = parser.parse_args()

    if args.append and args.replace:
        parser.error("--append y --replace son incompatibles.")
    if args.batch_size < 1:
        parser.error("--batch-size debe ser mayor que cero.")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds no puede ser negativo.")

    chunks = build_chunks(load_triage_guide(), dataset_version=args.dataset_version)
    _validate_chunks(chunks)

    counts: dict[str, int] = {}
    for tipo, _, _, _ in chunks:
        counts[tipo] = counts.get(tipo, 0) + 1
    print(f"Fragmentos generados: {len(chunks)}")
    for tipo, cantidad in counts.items():
        print(f"  - {tipo}: {cantidad}")

    if args.dry_run:
        for i, (tipo, nombre, contenido, source_key) in enumerate(chunks, start=1):
            print(f"\n[{i:02d}] ({tipo}) {nombre} [{source_key}] ({len(contenido)} chars)")
            print(contenido)
        print("\nDry run finalizado: no se llamo a Gemini ni a la base de datos.")
        return

    db = SessionLocal()
    inserted = updated = skipped = 0
    started = time.monotonic()
    try:
        source_keys = [source_key for _, _, _, source_key in chunks]
        if args.replace:
            removed = (
                db.query(KnowledgeChunk)
                .filter(~KnowledgeChunk.source_key.in_(source_keys))
                .delete(synchronize_session=False)
            )
            print(f"Filas fuera del dataset eliminadas: {removed}")

        for index, (tipo, nombre, contenido, source_key) in enumerate(chunks, start=1):
            existing = (
                db.query(KnowledgeChunk)
                .filter(KnowledgeChunk.source_key == source_key)
                .one_or_none()
            )
            if existing and existing.tipo == tipo and existing.nombre == nombre and existing.contenido == contenido:
                skipped += 1
                print(f"[{index:02d}/{len(chunks)}] sin cambios -> {nombre}")
                continue

            embedding = get_gemini_embedding(
                contenido,
                task_type="RETRIEVAL_DOCUMENT",
            )
            if len(embedding) != EMBEDDING_DIM:
                raise ValueError(
                    f"Embedding de dimension inesperada: {len(embedding)} != {EMBEDDING_DIM}."
                )

            if existing:
                existing.tipo = tipo
                existing.nombre = nombre
                existing.contenido = contenido
                existing.embedding = embedding
                updated += 1
                action = "actualizado"
            else:
                db.add(
                    KnowledgeChunk(
                        source_key=source_key,
                        tipo=tipo,
                        nombre=nombre,
                        contenido=contenido,
                        embedding=embedding,
                    )
                )
                inserted += 1
                action = "insertado"

            if (inserted + updated) % args.batch_size == 0:
                db.commit()
            print(f"[{index:02d}/{len(chunks)}] {action} -> {nombre}")
            if args.delay_seconds:
                time.sleep(args.delay_seconds)

        db.commit()
        elapsed = time.monotonic() - started
        print(
            f"\nIngesta completada en {elapsed:.1f}s: "
            f"insertados={inserted}, actualizados={updated}, omitidos={skipped}."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
