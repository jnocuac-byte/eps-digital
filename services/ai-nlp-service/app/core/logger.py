"""Logger centralizado con loguru y contextvars para trazabilidad contextualizada.

Uso:
    from app.core.logger import log_event
    log_event("ORCH", "TOOL_LOOP", "info", "Tool call detectado: obtener_especialidades")

El logger emite en formato:
    {time} | {level} | {module:<15} | {stage:<15} | {message}
"""
from __future__ import annotations

import os
import sys
import contextvars

from loguru import logger

# Context variables para etiquetas modulares
module_var: contextvars.ContextVar[str] = contextvars.ContextVar("module", default="APP")
stage_var: contextvars.ContextVar[str] = contextvars.ContextVar("stage", default="INIT")

_configured = False


def _format_record(record) -> str:
    """Formatea el registro resolviendo las context variables."""
    module = record["extra"].get("module", "APP")
    stage = record["extra"].get("stage", "INIT")
    # Resolver ContextVar a su valor
    if hasattr(module, "get"):
        module = module.get()
    if hasattr(stage, "get"):
        stage = stage.get()
    return (
        f"<green>{record['time'].strftime('%Y-%m-%d %H:%M:%S.SSS')}</green> | "
        f"<level>{record['level'].name: <8}</level> | "
        f"<cyan>{module:<15}</cyan> | "
        f"<magenta>{stage:<15}</magenta> | "
        f"<level>{record['message']}</level>"
    )


def setup_logger() -> None:
    """Configura el logger global una sola vez."""
    global _configured
    if _configured:
        return
    _configured = True

    logger.remove()

    log_level = os.getenv("LOG_LEVEL", "DEBUG")

    logger.add(
        sys.stdout,
        format=_format_record,
        level=log_level,
        colorize=True,
    )


def log_event(
    module: str,
    stage: str,
    level: str = "info",
    message: str = "",
) -> None:
    """Emite un log con contexto modular y de etapa.

    Args:
        module: Etiqueta del módulo (ej: "ORCH", "LLM", "TOOLS", "MAIN").
        stage: Etiqueta de la etapa (ej: "REQUEST", "FALLBACK", "HTTP").
        level: Nivel de log (debug, info, warning, error).
        message: Mensaje descriptivo del evento.
    """
    logger.bind(module=module, stage=stage).__getattribute__(level)(message)
