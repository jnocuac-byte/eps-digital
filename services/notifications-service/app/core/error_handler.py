"""Manejo centralizado de errores con logging para Notifications Service.

Registra exception handlers globales en FastAPI que capturan errores
de dominio y los convierten a respuestas HTTP consistentes con trazabilidad.

Uso en main.py:
    from app.core.error_handler import register_exception_handlers
    register_exception_handlers(app)
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.logger import log_event


class ServiceError(Exception):
    """Error base de dominio para el servicio."""

    def __init__(self, message: str = "Error interno del servicio", status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NotFoundError(ServiceError):
    """Entidad no encontrada."""

    def __init__(self, entity: str = "Recurso", entity_id: str = ""):
        detail = f"{entity} no encontrado" + (f": {entity_id}" if entity_id else "")
        super().__init__(message=detail, status_code=404)


class ValidationError(ServiceError):
    """Error de validacion de datos de entrada."""

    def __init__(self, message: str = "Datos de entrada invalidos"):
        super().__init__(message=message, status_code=400)


class EmailSendError(ServiceError):
    """Error al enviar correo electronico."""

    def __init__(self, message: str = "Error enviando correo"):
        super().__init__(message=message, status_code=502)


class RabbitMQError(ServiceError):
    """Error de conexion o comunicacion con RabbitMQ."""

    def __init__(self, message: str = "Error de conexion con RabbitMQ"):
        super().__init__(message=message, status_code=503)


def handle_value_error(exc: ValueError, default_status: int = 400) -> int:
    """Mapea ValueError a HTTP status segun el tipo de mensaje."""
    message = str(exc).lower()
    if "no existe" in message or "no encontrado" in message:
        return status.HTTP_404_NOT_FOUND
    return default_status


def register_exception_handlers(app: FastAPI) -> None:
    """Registra exception handlers globales en la aplicacion FastAPI."""

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        log_event(
            "ERROR", "HANDLER", "warning",
            f"[{request.method}] {request.url.path} -> {exc.status_code}: {exc.message}",
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        http_status = handle_value_error(exc)
        log_event(
            "ERROR", "HANDLER", "warning",
            f"[{request.method}] {request.url.path} -> {http_status}: {exc}",
        )
        return JSONResponse(
            status_code=http_status,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        log_event(
            "ERROR", "HANDLER", "error",
            f"[{request.method}] {request.url.path} -> 500: {type(exc).__name__}: {exc}",
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Error interno del servidor"},
        )
