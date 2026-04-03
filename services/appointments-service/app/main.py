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
	create_cita,
	create_recordatorio,
	delete_cita,
	get_cita_by_id,
	get_citas_by_estado,
	get_citas_by_medico,
	get_citas_by_usuario,
	get_historial_by_cita,
	get_recordatorios_pendientes,
	reprogramar_cita,
	update_cita,
)
from app.database import Base, engine, get_db
from app.schemas import (
	CancelarCitaRequest,
	CitaCreate,
	CitaResponse,
	CitaUpdate,
	ESTADOS_CITA_VALIDOS,
	HistorialEstadoResponse,
	RecordatorioResponse,
	ReprogramarCitaRequest,
)

from fastapi.middleware.cors import CORSMiddleware


class MessageResponse(BaseModel):
	"""Respuesta simple para operaciones sin payload complejo."""

	message: str
	success: bool = True


@asynccontextmanager
async def lifespan(_: FastAPI):
	"""Gestiona eventos de ciclo de vida de la aplicacion."""
	Base.metadata.create_all(bind=engine)
	yield


app = FastAPI(
	title="EPS Digital - Citas Service",
	version="1.0.0",
	description="Servicio para gestion de citas medicas, historial y recordatorios.",
	lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
	try:
		return create_cita(db, payload)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/citas/usuario/{usuario_id}", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_por_usuario(
	usuario_id: UUID,
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista las citas de un usuario con paginacion."""
	return get_citas_by_usuario(db, usuario_id, skip=skip, limit=limit)


@app.get("/citas/medico/{medico_id}", response_model=list[CitaResponse], tags=["citas"])
def listar_citas_por_medico(
	medico_id: UUID,
	fecha: date | None = Query(default=None),
	db: Session = Depends(get_db),
) -> list[CitaResponse]:
	"""Lista citas de un medico; permite filtrar por fecha."""
	return get_citas_by_medico(db, medico_id, fecha=fecha)


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
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="Estado invalido. Valores permitidos: programada, cancelada, atendida, no_asistio",
		)

	return get_citas_by_estado(db, estado_normalizado, skip=skip, limit=limit)


@app.get("/citas/{cita_id}", response_model=CitaResponse, tags=["citas"])
def obtener_cita(cita_id: UUID, db: Session = Depends(get_db)) -> CitaResponse:
	"""Obtiene una cita por su identificador."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
	return cita


@app.put("/citas/{cita_id}", response_model=CitaResponse, tags=["citas"])
def actualizar_cita(
	cita_id: UUID,
	payload: CitaUpdate,
	db: Session = Depends(get_db),
) -> CitaResponse:
	"""Actualiza parcialmente una cita."""
	try:
		return update_cita(db, cita_id, payload)
	except ValueError as exc:
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
	try:
		return cancelar_cita(db, cita_id, payload.motivo, realizado_por)
	except ValueError as exc:
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
	try:
		return reprogramar_cita(
			db,
			cita_id,
			payload.nueva_fecha,
			payload.nueva_hora_inicio,
			payload.nueva_hora_fin,
			realizado_por,
		)
	except ValueError as exc:
		mensaje = str(exc)
		status_code = status.HTTP_404_NOT_FOUND if "No existe cita" in mensaje else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=status_code, detail=mensaje) from exc


@app.delete("/citas/{cita_id}", response_model=MessageResponse, tags=["citas"])
def eliminar_cita(cita_id: UUID, db: Session = Depends(get_db)) -> MessageResponse:
	"""Elimina una cita de forma permanente."""
	try:
		delete_cita(db, cita_id)
		return MessageResponse(message="Cita eliminada correctamente", success=True)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/citas/{cita_id}/historial", response_model=list[HistorialEstadoResponse], tags=["citas"])
def obtener_historial_cita(cita_id: UUID, db: Session = Depends(get_db)) -> list[HistorialEstadoResponse]:
	"""Obtiene el historial de cambios de estado de una cita."""
	if not get_cita_by_id(db, cita_id):
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
	return get_historial_by_cita(db, cita_id)


@app.post(
	"/citas/{cita_id}/recordatorio",
	response_model=RecordatorioResponse,
	tags=["citas"],
)
def crear_recordatorio_cita(cita_id: UUID, db: Session = Depends(get_db)) -> RecordatorioResponse:
	"""Programa un recordatorio 24 horas antes de la cita."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")

	programado_para = datetime.combine(cita.fecha_cita, cita.hora_inicio) - timedelta(hours=24)

	try:
		return create_recordatorio(db, cita_id=cita_id, programado_para=programado_para)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/recordatorios/pendientes", response_model=list[RecordatorioResponse], tags=["citas"])
def listar_recordatorios_pendientes(db: Session = Depends(get_db)) -> list[RecordatorioResponse]:
	"""Obtiene recordatorios pendientes de envio hasta el momento actual."""
	return get_recordatorios_pendientes(db)
