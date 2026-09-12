"""API principal del Citas Service."""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud import (
	cancelar_cita,
	cambiar_estado_cita,
	create_cita,
	create_recordatorio,
	delete_cita,
	generar_slots_disponibles,
	get_cita_by_id,
	get_citas_by_estado,
	get_citas_by_medico,
	get_citas_by_usuario,
	get_citas_historicas_by_usuario,
	get_historial_by_cita,
	get_metricas_citas,
	get_metricas_medico,
	get_recordatorios_pendientes,
	reprogramar_cita,
	update_cita,
)
from app.database import Base, engine, get_db
from app.core.logger import setup_logger, log_event
from app.core.error_handler import register_exception_handlers
from app.schemas import (
	CancelarCitaRequest,
	CambioEstadoRequest,
	CitaCreate,
	CitaResponse,
	CitaUpdate,
	ESTADOS_CITA_VALIDOS,
	HistorialEstadoResponse,
	RecordatorioResponse,
	ReprogramarCitaRequest,
	SlotDisponible,
)

from fastapi.middleware.cors import CORSMiddleware


class MessageResponse(BaseModel):
	"""Respuesta simple para operaciones sin payload complejo."""

	message: str
	success: bool = True


@asynccontextmanager
async def lifespan(_: FastAPI):
	"""Gestiona eventos de ciclo de vida de la aplicacion."""
	setup_logger()
	log_event("MAIN", "INIT", "info", "Iniciando Appointments Service...")
	Base.metadata.create_all(bind=engine)
	log_event("MAIN", "INIT", "info", "Base de datos inicializada")
	log_event("MAIN", "INIT", "info", "Appointments Service listo")
	yield
	log_event("MAIN", "SHUTDOWN", "info", "Appointments Service finalizando")


app = FastAPI(
	title="EPS Digital - Citas Service",
	version="1.0.0",
	description="Servicio para gestion de citas medicas, historial y recordatorios.",
	lifespan=lifespan,
)

register_exception_handlers(app)

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

def _parse_user_id_header(x_user_id: str | None) -> UUID:
	"""Convierte el header X-User-ID a UUID y valida su presencia."""
	if not x_user_id:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Header X-User-ID es requerido",
		)

	try:
		return UUID(x_user_id)
	except ValueError as exc:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Header X-User-ID no es un UUID valido",
		) from exc

	
@app.post("/citas", response_model=CitaResponse, tags=["citas"])
def crear_cita(payload: CitaCreate, db: Session = Depends(get_db)) -> CitaResponse:
	"""Crea una cita nueva."""
	log_event("CITAS", "CREATE", "info", f"Solicitud crear cita: usuario={payload.usuario_id}, fecha={payload.fecha_cita}")
	try:
		cita = create_cita(db, payload)
		log_event("CITAS", "CREATE", "info", f"Cita creada: cita_id={cita.cita_id}")
		return cita
	except ValueError as exc:
		log_event("CITAS", "CREATE", "warning", f"Error creando cita: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/citas/usuario/{usuario_id}", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_por_usuario(
	usuario_id: UUID,
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista las citas de un usuario con paginacion."""
	log_event("CITAS", "LIST", "debug", f"Listar citas usuario={usuario_id}, skip={skip}, limit={limit}")
	return get_citas_by_usuario(db, usuario_id, skip=skip, limit=limit)


@app.get("/citas/usuario/{usuario_id}/historial", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_historicas(
	usuario_id: UUID,
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista las citas historicas (canceladas, atendidas, no asistio) de un usuario."""
	log_event("CITAS", "LIST_HIST", "debug", f"Listar historial usuario={usuario_id}")
	return get_citas_historicas_by_usuario(db, usuario_id, skip=skip, limit=limit)


@app.get("/citas/medico/{medico_id}", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_por_medico(
	medico_id: UUID,
	fecha: date | None = Query(default=None),
	fecha_inicio: date | None = Query(default=None),
	fecha_fin: date | None = Query(default=None),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista citas de un medico; permite filtrar por fecha unica o rango de fechas."""
	log_event("CITAS", "LIST_MED", "debug", f"Listar citas medico={medico_id}")
	return get_citas_by_medico(db, medico_id, fecha=fecha, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)


@app.get("/citas/estado/{estado}", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_por_estado(
	estado: str,
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista citas por estado."""
	estado_normalizado = estado.strip().lower()
	if estado_normalizado not in ESTADOS_CITA_VALIDOS:
		log_event("CITAS", "LIST_STATE", "warning", f"Estado invalido: {estado}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Estado invalido. Valores permitidos: programada, cancelada, atendida, no_asistio",
		)

	log_event("CITAS", "LIST_STATE", "debug", f"Listar citas estado={estado_normalizado}")
	return get_citas_by_estado(db, estado_normalizado, skip=skip, limit=limit)


@app.get("/citas/slots-disponibles", response_model=list[SlotDisponible], tags=["citas"])
def listar_slots_disponibles(
	fecha: date = Query(...),
	medico_id: UUID | None = Query(default=None),
	servicio_id: UUID | None = Query(default=None),
	especialidad_id: UUID | None = Query(default=None),
	db: Session = Depends(get_db),
) -> list[SlotDisponible]:
	"""Franjas horarias disponibles para agendar (reglas en America/Bogota)."""
	log_event("CITAS", "SLOTS", "info", f"Consultar slots fecha={fecha}, medico={medico_id}")
	try:
		slots = generar_slots_disponibles(
			db,
			fecha=fecha,
			medico_id=medico_id,
			servicio_id=servicio_id,
			especialidad_id=especialidad_id,
		)
	except ValueError as exc:
		log_event("CITAS", "SLOTS", "warning", f"Error consultando slots: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
	log_event("CITAS", "SLOTS", "info", f"Slots disponibles: {len(slots)}")
	return [SlotDisponible(**slot) for slot in slots]


@app.get("/citas/metricas", tags=["admin"])
def obtener_metricas(
	dias: int = Query(default=7, ge=1, le=90),
	db: Session = Depends(get_db),
) -> dict:
	"""Obtiene metricas agregadas de citas para dashboard administrativo."""
	log_event("CITAS", "METRICS", "info", f"Metricas solicitadas: dias={dias}")
	return get_metricas_citas(db, dias=dias)


@app.get("/citas/medico/{medico_id}/metricas", tags=["medico"])
def obtener_metricas_medico(
	medico_id: UUID,
	db: Session = Depends(get_db),
) -> dict:
	"""Obtiene metricas del dashboard para un medico especifico."""
	log_event("CITAS", "METRICS_MED", "info", f"Metricas medico solicitadas: medico={medico_id}")
	return get_metricas_medico(db, medico_id=medico_id)


@app.get("/citas/{cita_id}", response_model=CitaResponse, tags=["citas"])
def obtener_cita(cita_id: UUID, db: Session = Depends(get_db)) -> CitaResponse:
	"""Obtiene una cita por su identificador."""
	log_event("CITAS", "GET", "debug", f"Obtener cita={cita_id}")
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		log_event("CITAS", "GET", "warning", f"Cita no encontrada: {cita_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
	return cita


@app.put("/citas/{cita_id}", response_model=CitaResponse, tags=["citas"])
def actualizar_cita(
	cita_id: UUID,
	payload: CitaUpdate,
	db: Session = Depends(get_db),
) -> CitaResponse:
	"""Actualiza parcialmente una cita."""
	log_event("CITAS", "UPDATE", "info", f"Actualizar cita={cita_id}")
	try:
		cita = update_cita(db, cita_id, payload)
		log_event("CITAS", "UPDATE", "info", f"Cita actualizada: {cita_id}")
		return cita
	except ValueError as exc:
		log_event("CITAS", "UPDATE", "warning", f"Error actualizando cita {cita_id}: {exc}")
		mensaje = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if "No existe cita" in mensaje else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=status_code, detail=mensaje) from exc


@app.post("/citas/{cita_id}/cancelar", response_model=CitaResponse, tags=["citas"])
def cancelar_cita_endpoint(
	cita_id: UUID,
	payload: CancelarCitaRequest,
	x_user_id: str | None = Header(default=None, alias="X-User-ID"),
	db: Session = Depends(get_db),
) -> CitaResponse:
	"""Cancela una cita si cumple reglas de negocio."""
	realizado_por = _parse_user_id_header(x_user_id)
	log_event("CITAS", "CANCEL", "info", f"Cancelar cita={cita_id}, por={realizado_por}")
	try:
		cita = cancelar_cita(db, cita_id, payload.motivo, realizado_por)
		log_event("CITAS", "CANCEL", "info", f"Cita cancelada: {cita_id}")
		return cita
	except ValueError as exc:
		log_event("CITAS", "CANCEL", "warning", f"Error cancelando cita {cita_id}: {exc}")
		mensaje = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if "No existe cita" in mensaje else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=status_code, detail=mensaje) from exc


@app.patch("/citas/{cita_id}/estado", response_model=CitaResponse, tags=["medico"])
def cambiar_estado_cita_endpoint(
	cita_id: UUID,
	payload: CambioEstadoRequest,
	x_user_id: str | None = Header(default=None, alias="X-User-ID"),
	db: Session = Depends(get_db),
) -> CitaResponse:
	"""Cambia el estado de una cita programada (atendida, no_asistio, cancelada)."""
	realizado_por = _parse_user_id_header(x_user_id)
	log_event("CITAS", "CHANGE_STATE", "info", f"Cambiar estado cita={cita_id} a {payload.estado}, por={realizado_por}")
	try:
		cita = cambiar_estado_cita(
			db,
			cita_id,
			nuevo_estado=payload.estado,
			motivo=payload.motivo,
			realizado_por=realizado_por,
		)
		log_event("CITAS", "CHANGE_STATE", "info", f"Estado cambiado en cita={cita_id}")
		return cita
	except ValueError as exc:
		log_event("CITAS", "CHANGE_STATE", "warning", f"Error cambiando estado cita {cita_id}: {exc}")
		mensaje = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if "No existe cita" in mensaje else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=status_code, detail=mensaje) from exc


@app.post("/citas/{cita_id}/reprogramar", response_model=CitaResponse, tags=["citas"])
def reprogramar_cita_endpoint(
	cita_id: UUID,
	payload: ReprogramarCitaRequest,
	x_user_id: str | None = Header(default=None, alias="X-User-ID"),
	db: Session = Depends(get_db),
) -> CitaResponse:
	"""Reprograma una cita validando disponibilidad."""
	realizado_por = _parse_user_id_header(x_user_id)
	log_event("CITAS", "RESCHEDULE", "info", f"Reprogramar cita={cita_id}, nueva_fecha={payload.nueva_fecha}, por={realizado_por}")
	try:
		cita = reprogramar_cita(
			db,
			cita_id,
			payload.nueva_fecha,
			payload.nueva_hora_inicio,
			payload.nueva_hora_fin,
			realizado_por,
			motivo=payload.motivo,
		)
		log_event("CITAS", "RESCHEDULE", "info", f"Cita reprogramada: {cita_id}")
		return cita
	except ValueError as exc:
		log_event("CITAS", "RESCHEDULE", "warning", f"Error reprogramando cita {cita_id}: {exc}")
		mensaje = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if "No existe cita" in mensaje else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=status_code, detail=mensaje) from exc


@app.delete("/citas/{cita_id}", response_model=MessageResponse, tags=["citas"])
def eliminar_cita(cita_id: UUID, db: Session = Depends(get_db)) -> MessageResponse:
	"""Elimina una cita de forma permanente."""
	log_event("CITAS", "DELETE", "warning", f"Eliminar cita={cita_id}")
	try:
		delete_cita(db, cita_id)
		log_event("CITAS", "DELETE", "info", f"Cita eliminada: {cita_id}")
		return MessageResponse(message="Cita eliminada correctamente", success=True)
	except ValueError as exc:
		log_event("CITAS", "DELETE", "warning", f"Error eliminando cita {cita_id}: {exc}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/citas/{cita_id}/historial", response_model=list[HistorialEstadoResponse], tags=["citas"])
def obtener_historial_cita(cita_id: UUID, db: Session = Depends(get_db)) -> list[HistorialEstadoResponse]:
	"""Obtiene el historial de cambios de estado de una cita."""
	log_event("CITAS", "HISTORY", "debug", f"Historial cita={cita_id}")
	if not get_cita_by_id(db, cita_id):
		log_event("CITAS", "HISTORY", "warning", f"Cita no encontrada para historial: {cita_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
	return get_historial_by_cita(db, cita_id)


@app.post(
	"/citas/{cita_id}/recordatorio",
	response_model=RecordatorioResponse,
	tags=["citas"],
)
def crear_recordatorio_cita(cita_id: UUID, db: Session = Depends(get_db)) -> RecordatorioResponse:
	"""Programa un recordatorio 24 horas antes de la cita."""
	log_event("CITAS", "REMINDER", "info", f"Crear recordatorio para cita={cita_id}")
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		log_event("CITAS", "REMINDER", "warning", f"Cita no encontrada para recordatorio: {cita_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

	programado_para = datetime.combine(cita.fecha_cita, cita.hora_inicio) - timedelta(hours=24)

	try:
		reminder = create_recordatorio(db, cita_id=cita_id, programado_para=programado_para)
		log_event("CITAS", "REMINDER", "info", f"Recordatorio creado para cita={cita_id}")
		return reminder
	except ValueError as exc:
		log_event("CITAS", "REMINDER", "warning", f"Error creando recordatorio: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/recordatorios/pendientes", response_model=list[RecordatorioResponse], tags=["citas"])
def listar_recordatorios_pendientes(db: Session = Depends(get_db)) -> list[RecordatorioResponse]:
	"""Obtiene recordatorios pendientes de envio hasta el momento actual."""
	log_event("CITAS", "REMINDERS", "debug", "Listar recordatorios pendientes")
	return get_recordatorios_pendientes(db)
