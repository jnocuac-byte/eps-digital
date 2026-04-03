import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from .consumer import configurar_rabbitmq, start_background_consumer
from .email_client import configurar_sendgrid, enviar_correo
from .templates import bienvenida

from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEmailRequest(BaseModel):
	"""Payload para el endpoint de prueba de correo."""

	email: EmailStr


class MessageResponse(BaseModel):
	"""Respuesta estándar para operaciones del servicio."""

	message: str


# Contadores simples en memoria para métricas básicas del servicio.
_stats_lock = threading.Lock()
_email_stats: Dict[str, Any] = {
	"emails_enviados": 0,
	"emails_fallidos": 0,
	"ultima_fecha_envio": None,
	"ultimo_error": None,
}


def _set_stat(key: str, value: Any) -> None:
	with _stats_lock:
		_email_stats[key] = value


def _increment_stat(key: str) -> None:
	with _stats_lock:
		_email_stats[key] = int(_email_stats.get(key, 0)) + 1


def _get_stats_snapshot() -> Dict[str, Any]:
	with _stats_lock:
		return dict(_email_stats)


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Inicializa recursos del servicio al arrancar la aplicación."""
	del app

	configurar_sendgrid()
	consumer_thread = start_background_consumer()
	logger.info("Notifications Service iniciado. Consumer activo: %s", consumer_thread.is_alive())

	yield

	# El hilo consumidor es daemon, por lo que se cerrará automáticamente al apagar.
	logger.info("Notifications Service finalizando.")


app = FastAPI(title="Notifications Service", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite dev
        "http://localhost:3000",      # React alternativo
        "https://eps-digital.onrender.com",  # Frontend en Render
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> Dict[str, str]:
	"""Endpoint de salud del servicio y conectividad a RabbitMQ."""
	rabbitmq_status = "disconnected"
	connection = None

	try:
		connection, _ = configurar_rabbitmq()
		rabbitmq_status = "connected"
	except Exception:
		logger.exception("No fue posible conectar a RabbitMQ desde /health.")
	finally:
		if connection and connection.is_open:
			try:
				connection.close()
			except Exception:
				logger.exception("Error cerrando conexión temporal de /health.")

	return {"status": "ok", "rabbitmq": rabbitmq_status}


@app.get("/stats")
def stats() -> Dict[str, Any]:
	"""Retorna contadores simples en memoria de envíos de correo."""
	return _get_stats_snapshot()


@app.post("/test-email", response_model=MessageResponse)
def test_email(payload: TestEmailRequest) -> MessageResponse:
	"""Envía un correo de prueba usando la plantilla de bienvenida."""
	contenido = bienvenida("Usuario de prueba")
	enviado = enviar_correo(
		destinatario=payload.email,
		asunto="Correo de prueba - Notifications Service",
		contenido_html=contenido,
	)

	if enviado:
		_increment_stat("emails_enviados")
		_set_stat("ultima_fecha_envio", datetime.now(timezone.utc).isoformat())
		_set_stat("ultimo_error", None)
		return MessageResponse(message="Correo de prueba enviado correctamente")

	_increment_stat("emails_fallidos")
	_set_stat("ultimo_error", "No se pudo enviar el correo de prueba")
	raise HTTPException(status_code=500, detail="Error enviando correo de prueba")
