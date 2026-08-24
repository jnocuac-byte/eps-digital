"""API principal del Notifications Service."""

import logging
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .consumer import configurar_rabbitmq, start_background_consumer
from .database import Base, engine, get_db
from .email_client import configurar_sendgrid, enviar_correo
from .models import Notificacion
from .schemas import NotificacionCreate, NotificacionResponse, MessageResponse
from .templates import bienvenida

from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestEmailRequest(BaseModel):
	email: EmailStr


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
	Base.metadata.create_all(bind=engine)
	configurar_sendgrid()
	consumer_thread = start_background_consumer()
	logger.info("Notifications Service iniciado. Consumer activo: %s", consumer_thread.is_alive())
	yield
	logger.info("Notifications Service finalizando.")


app = FastAPI(title="Notifications Service", version="1.0.0", lifespan=lifespan)

origins = [
    "https://eps-digital-cn2h.onrender.com",
    "https://eps-digital-cn2h.onrender.com/",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5173/",
    "http://127.0.0.1:5173/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-User-ID"],
	max_age=600,
)


@app.get("/health")
def health() -> Dict[str, str]:
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
				logger.exception("Error cerrando conexion temporal de /health.")
	return {"status": "ok", "rabbitmq": rabbitmq_status}


@app.get("/stats")
def stats() -> Dict[str, Any]:
	return _get_stats_snapshot()


@app.post("/test-email", response_model=MessageResponse)
def test_email(payload: TestEmailRequest) -> MessageResponse:
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


@app.post("/notificaciones", response_model=NotificacionResponse, tags=["notificaciones"])
def crear_notificacion(payload: NotificacionCreate, db: Session = Depends(get_db)) -> NotificacionResponse:
	notif = Notificacion(
		medico_id=payload.medico_id,
		tipo=payload.tipo,
		titulo=payload.titulo,
		descripcion=payload.descripcion,
		enlace=payload.enlace,
	)
	db.add(notif)
	db.commit()
	db.refresh(notif)
	return notif


@app.get("/notificaciones/medico/{medico_id}", response_model=list[NotificacionResponse], tags=["notificaciones"])
def listar_notificaciones_medico(
	medico_id: UUID,
	db: Session = Depends(get_db),
) -> list[NotificacionResponse]:
	stmt = (
		select(Notificacion)
		.where(Notificacion.medico_id == medico_id)
		.order_by(Notificacion.creado_en.desc())
		.limit(50)
	)
	return list(db.scalars(stmt).all())


@app.patch("/notificaciones/{notif_id}/leida", response_model=MessageResponse, tags=["notificaciones"])
def marcar_leida(notif_id: UUID, db: Session = Depends(get_db)) -> MessageResponse:
	stmt = select(Notificacion).where(Notificacion.notif_id == notif_id)
	notif = db.scalar(stmt)
	if not notif:
		raise HTTPException(status_code=404, detail="Notificacion no encontrada")
	notif.leida = True
	db.commit()
	return MessageResponse(message="Notificacion marcada como leida")


@app.patch("/notificaciones/medico/{medico_id}/leer-todas", response_model=MessageResponse, tags=["notificaciones"])
def marcar_todas_leidas(medico_id: UUID, db: Session = Depends(get_db)) -> MessageResponse:
	stmt = update(Notificacion).where(
		Notificacion.medico_id == medico_id,
		Notificacion.leida == False,
	).values(leida=True)
	db.execute(stmt)
	db.commit()
	return MessageResponse(message="Todas las notificaciones marcadas como leidas")
