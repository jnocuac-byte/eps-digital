from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, time
from importlib import import_module
from uuid import UUID


from fastapi import Depends, FastAPI, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi.middleware.cors import CORSMiddleware

try:
	crud = import_module("app.crud")
	_database = import_module("app.database")
	_models = import_module("app.models")
	_schemas = import_module("app.schemas")
except ModuleNotFoundError:
	# Permite ejecucion local cuando el cwd es app/.
	crud = import_module("crud")
	_database = import_module("database")
	_models = import_module("models")
	_schemas = import_module("schemas")

from app.core.logger import setup_logger, log_event
from app.core.error_handler import register_exception_handlers

engine = _database.engine
get_db = _database.get_db
Base = _models.Base

DisponibilidadCreate = _schemas.DisponibilidadCreate
DisponibilidadResponse = _schemas.DisponibilidadResponse
DisponibilidadUpdate = _schemas.DisponibilidadUpdate
EspecialidadCreate = _schemas.EspecialidadCreate
EspecialidadResponse = _schemas.EspecialidadResponse
EspecialidadUpdate = _schemas.EspecialidadUpdate
MedicoEspecialidadResponse = _schemas.MedicoEspecialidadResponse
MedicoCreate = _schemas.MedicoCreate
MedicoResponse = _schemas.MedicoResponse
MedicoUpdate = _schemas.MedicoUpdate
SedeCreate = _schemas.SedeCreate
SedeResponse = _schemas.SedeResponse
SedeUpdate = _schemas.SedeUpdate
ServicioCreate = _schemas.ServicioCreate
ServicioResponse = _schemas.ServicioResponse
ServicioUpdate = _schemas.ServicioUpdate


@asynccontextmanager
async def lifespan(_: FastAPI):
	"""Inicializa recursos del servicio al arrancar la aplicacion."""
	setup_logger()
	log_event("MAIN", "INIT", "info", "Iniciando Catalog Service...")
	Base.metadata.create_all(bind=engine)
	log_event("MAIN", "INIT", "info", "Base de datos inicializada")
	log_event("MAIN", "INIT", "info", "Catalog Service listo")
	yield
	log_event("MAIN", "SHUTDOWN", "info", "Catalog Service finalizando")


app = FastAPI(
	title="EPS Digital - Catalogo Service",
	version="1.0.0",
	description="Servicio de catalogo medico para servicios, especialidades y disponibilidad.",
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

# SERVICIOS
@app.post(
	"/servicios",
	response_model=ServicioResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Servicios"],
)
def crear_servicio(payload: ServicioCreate, db: Session = Depends(get_db)) -> ServicioResponse:
	log_event("CATALOG", "CREATE_SERVICIO", "info", f"Crear servicio: {payload.nombre}")
	try:
		servicio = crud.create_servicio(db, payload)
		log_event("CATALOG", "CREATE_SERVICIO", "info", f"Servicio creado: {servicio.servicio_id}")
		return servicio
	except Exception as exc:
		log_event("CATALOG", "CREATE_SERVICIO", "warning", f"Error creando servicio: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/servicios", response_model=list[ServicioResponse], tags=["Servicios"])
def listar_servicios(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[ServicioResponse]:
	log_event("CATALOG", "LIST_SERVICIOS", "debug", f"Listar servicios skip={skip} limit={limit}")
	return crud.get_servicios(db, skip=skip, limit=limit, solo_activos=solo_activos)


@app.get("/servicios/{servicio_id}", response_model=ServicioResponse, tags=["Servicios"])
def obtener_servicio(servicio_id: UUID, db: Session = Depends(get_db)) -> ServicioResponse:
	log_event("CATALOG", "GET_SERVICIO", "debug", f"Obtener servicio={servicio_id}")
	servicio = crud.get_servicio_by_id(db, servicio_id)
	if servicio is None:
		log_event("CATALOG", "GET_SERVICIO", "warning", f"Servicio no encontrado: {servicio_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
	return servicio


@app.put("/servicios/{servicio_id}", response_model=ServicioResponse, tags=["Servicios"])
def actualizar_servicio(
	servicio_id: UUID,
	payload: ServicioUpdate,
	db: Session = Depends(get_db),
) -> ServicioResponse:
	log_event("CATALOG", "UPDATE_SERVICIO", "info", f"Actualizar servicio={servicio_id}")
	try:
		servicio = crud.update_servicio(db, servicio_id, payload)
		log_event("CATALOG", "UPDATE_SERVICIO", "info", f"Servicio actualizado: {servicio_id}")
		return servicio
	except ValueError as exc:
		log_event("CATALOG", "UPDATE_SERVICIO", "warning", f"Error actualizando servicio {servicio_id}: {exc}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/servicios/{servicio_id}", tags=["Servicios"])
def eliminar_servicio(servicio_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	log_event("CATALOG", "DELETE_SERVICIO", "info", f"Eliminar servicio={servicio_id}")
	deleted = crud.delete_servicio(db, servicio_id)
	if not deleted:
		log_event("CATALOG", "DELETE_SERVICIO", "warning", f"Servicio no encontrado: {servicio_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
	return {"success": True}


# ESPECIALIDADES
@app.post(
	"/especialidades",
	response_model=EspecialidadResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Especialidades"],
)
def crear_especialidad(
	payload: EspecialidadCreate, db: Session = Depends(get_db)
) -> EspecialidadResponse:
	log_event("CATALOG", "CREATE_ESPECIALIDAD", "info", f"Crear especialidad: {payload.nombre}")
	try:
		esp = crud.create_especialidad(db, payload)
		log_event("CATALOG", "CREATE_ESPECIALIDAD", "info", f"Especialidad creada: {esp.especialidad_id}")
		return esp
	except ValueError as exc:
		log_event("CATALOG", "CREATE_ESPECIALIDAD", "warning", f"Error creando especialidad: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/especialidades", response_model=list[EspecialidadResponse], tags=["Especialidades"])
def listar_especialidades(
	servicio_id: UUID | None = Query(default=None),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[EspecialidadResponse]:
	log_event("CATALOG", "LIST_ESPECIALIDADES", "debug", f"Listar especialidades servicio={servicio_id}")
	return crud.get_especialidades(db, servicio_id=servicio_id, solo_activos=solo_activos)


@app.get(
	"/especialidades/{especialidad_id}",
	response_model=EspecialidadResponse,
	tags=["Especialidades"],
)
def obtener_especialidad(especialidad_id: UUID, db: Session = Depends(get_db)) -> EspecialidadResponse:
	log_event("CATALOG", "GET_ESPECIALIDAD", "debug", f"Obtener especialidad={especialidad_id}")
	especialidad = crud.get_especialidad_by_id(db, especialidad_id)
	if especialidad is None:
		log_event("CATALOG", "GET_ESPECIALIDAD", "warning", f"Especialidad no encontrada: {especialidad_id}")
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada"
		)
	return especialidad


@app.put(
	"/especialidades/{especialidad_id}",
	response_model=EspecialidadResponse,
	tags=["Especialidades"],
)
def actualizar_especialidad(
	especialidad_id: UUID,
	payload: EspecialidadUpdate,
	db: Session = Depends(get_db),
) -> EspecialidadResponse:
	log_event("CATALOG", "UPDATE_ESPECIALIDAD", "info", f"Actualizar especialidad={especialidad_id}")
	try:
		esp = crud.update_especialidad(db, especialidad_id, payload)
		log_event("CATALOG", "UPDATE_ESPECIALIDAD", "info", f"Especialidad actualizada: {especialidad_id}")
		return esp
	except ValueError as exc:
		log_event("CATALOG", "UPDATE_ESPECIALIDAD", "warning", f"Error actualizando especialidad {especialidad_id}: {exc}")
		msg = str(exc)
		code = status.HTTP_404_NOT_FOUND if "no encontrada" in msg else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=code, detail=msg) from exc


@app.delete("/especialidades/{especialidad_id}", tags=["Especialidades"])
def eliminar_especialidad(
	especialidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	log_event("CATALOG", "DELETE_ESPECIALIDAD", "info", f"Eliminar especialidad={especialidad_id}")
	deleted = crud.delete_especialidad(db, especialidad_id)
	if not deleted:
		log_event("CATALOG", "DELETE_ESPECIALIDAD", "warning", f"Especialidad no encontrada: {especialidad_id}")
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail="Especialidad no encontrada"
		)
	return {"success": True}


# MEDICOS
@app.post(
	"/medicos",
	response_model=MedicoResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Medicos"],
)
def crear_medico(payload: MedicoCreate, db: Session = Depends(get_db)) -> MedicoResponse:
	log_event("CATALOG", "CREATE_MEDICO", "info", f"Crear medico: {payload.nombres} {payload.apellidos}")
	try:
		medico = crud.create_medico(db, payload)
		log_event("CATALOG", "CREATE_MEDICO", "info", f"Medico creado: {medico.medico_id}")
		return medico
	except Exception as exc:
		log_event("CATALOG", "CREATE_MEDICO", "warning", f"Error creando medico: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/medicos", response_model=list[MedicoResponse], tags=["Medicos"])
def listar_medicos(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[MedicoResponse]:
	log_event("CATALOG", "LIST_MEDICOS", "debug", f"Listar medicos skip={skip} limit={limit}")
	return crud.get_medicos(db, skip=skip, limit=limit, solo_activos=solo_activos)


@app.get(
	"/medicos/disponibles",
	response_model=list[MedicoResponse],
	tags=["Medicos"],
)
def listar_medicos_disponibles(
	servicio_id: UUID | None = Query(default=None),
	especialidad_id: UUID | None = Query(default=None),
	fecha: date | None = Query(default=None),
	hora_inicio: time | None = Query(default=None),
	hora_fin: time | None = Query(default=None),
	db: Session = Depends(get_db),
) -> list[MedicoResponse]:
	"""Lista medicos disponibles segun filtros de servicio, especialidad y disponibilidad."""
	log_event("CATALOG", "MEDICOS_DISP", "info", f"Medicos disponibles: serv={servicio_id}, esp={especialidad_id}, fecha={fecha}")
	return crud.get_medicos_disponibles(
		db,
		servicio_id=servicio_id,
		especialidad_id=especialidad_id,
		fecha=fecha,
		hora_inicio=hora_inicio,
		hora_fin=hora_fin,
	)


@app.get(
	"/medicos/registro/{numero_registro}",
	response_model=MedicoResponse,
	tags=["Medicos"],
)
def obtener_medico_por_registro(
	numero_registro: str, db: Session = Depends(get_db)
) -> MedicoResponse:
	log_event("CATALOG", "GET_MEDICO_REG", "debug", f"Obtener medico por registro={numero_registro}")
	medico = crud.get_medico_by_registro(db, numero_registro)
	if medico is None:
		log_event("CATALOG", "GET_MEDICO_REG", "warning", f"Medico no encontrado: registro={numero_registro}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
	return medico


@app.get("/medicos/{medico_id}", response_model=MedicoResponse, tags=["Medicos"])
def obtener_medico(medico_id: UUID, db: Session = Depends(get_db)) -> MedicoResponse:
	log_event("CATALOG", "GET_MEDICO", "debug", f"Obtener medico={medico_id}")
	medico = crud.get_medico_by_id(db, medico_id)
	if medico is None:
		log_event("CATALOG", "GET_MEDICO", "warning", f"Medico no encontrado: {medico_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
	return medico


@app.put("/medicos/{medico_id}", response_model=MedicoResponse, tags=["Medicos"])
def actualizar_medico(
	medico_id: UUID,
	payload: MedicoUpdate,
	db: Session = Depends(get_db),
) -> MedicoResponse:
	log_event("CATALOG", "UPDATE_MEDICO", "info", f"Actualizar medico={medico_id}")
	try:
		medico = crud.update_medico(db, medico_id, payload)
		log_event("CATALOG", "UPDATE_MEDICO", "info", f"Medico actualizado: {medico_id}")
		return medico
	except ValueError as exc:
		log_event("CATALOG", "UPDATE_MEDICO", "warning", f"Error actualizando medico {medico_id}: {exc}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/medicos/{medico_id}", tags=["Medicos"])
def eliminar_medico(medico_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	log_event("CATALOG", "DELETE_MEDICO", "info", f"Eliminar medico={medico_id}")
	deleted = crud.delete_medico(db, medico_id)
	if not deleted:
		log_event("CATALOG", "DELETE_MEDICO", "warning", f"Medico no encontrado: {medico_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
	return {"success": True}


# MEDICO-ESPECIALIDAD
@app.post(
	"/medicos/{medico_id}/especialidades/{especialidad_id}",
	response_model=MedicoEspecialidadResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Medico-Especialidad"],
)
def asignar_especialidad_medico(
	medico_id: UUID,
	especialidad_id: UUID,
	es_principal: bool = Query(default=False),
	db: Session = Depends(get_db),
) -> MedicoEspecialidadResponse:
	log_event("CATALOG", "ASIGN_ESP", "info", f"Asignar especialidad={especialidad_id} a medico={medico_id}, principal={es_principal}")
	try:
		asignacion = crud.assign_especialidad_to_medico(
			db,
			medico_id=medico_id,
			especialidad_id=especialidad_id,
			es_principal=es_principal,
		)
		log_event("CATALOG", "ASIGN_ESP", "info", f"Especialidad asignada: medico={medico_id}")
		return asignacion
	except ValueError as exc:
		log_event("CATALOG", "ASIGN_ESP", "warning", f"Error asignando especialidad: {exc}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete(
	"/medico-especialidades/{medico_especialidad_id}",
	tags=["Medico-Especialidad"],
)
def remover_especialidad_medico(
	medico_especialidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	log_event("CATALOG", "REMOVE_ESP", "info", f"Remover asignacion={medico_especialidad_id}")
	deleted = crud.remove_especialidad_from_medico(db, medico_especialidad_id)
	if not deleted:
		log_event("CATALOG", "REMOVE_ESP", "warning", f"Asignacion no encontrada: {medico_especialidad_id}")
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Asignacion medico-especialidad no encontrada",
		)
	return {"success": True}


@app.get(
	"/medicos/{medico_id}/especialidades",
	response_model=list[MedicoEspecialidadResponse],
	tags=["Medico-Especialidad"],
)
def listar_especialidades_medico(
	medico_id: UUID, db: Session = Depends(get_db)
) -> list[MedicoEspecialidadResponse]:
	log_event("CATALOG", "LIST_ESP_MED", "debug", f"Especialidades de medico={medico_id}")
	return crud.get_medico_especialidades(db, medico_id)


@app.get(
	"/especialidades/{especialidad_id}/medicos",
	response_model=list[MedicoEspecialidadResponse],
	tags=["Medico-Especialidad"],
)
def listar_medicos_especialidad(
	especialidad_id: UUID, db: Session = Depends(get_db)
) -> list[MedicoEspecialidadResponse]:
	log_event("CATALOG", "LIST_MED_ESP", "debug", f"Medicos de especialidad={especialidad_id}")
	return crud.get_especialidad_medicos(db, especialidad_id)


# SEDES
@app.post(
	"/sedes",
	response_model=SedeResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Sedes"],
)
def crear_sede(payload: SedeCreate, db: Session = Depends(get_db)) -> SedeResponse:
	log_event("CATALOG", "CREATE_SEDE", "info", f"Crear sede: {payload.nombre}")
	try:
		sede = crud.create_sede(db, payload)
		log_event("CATALOG", "CREATE_SEDE", "info", f"Sede creada: {sede.sede_id}")
		return sede
	except Exception as exc:
		log_event("CATALOG", "CREATE_SEDE", "warning", f"Error creando sede: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/sedes", response_model=list[SedeResponse], tags=["Sedes"])
def listar_sedes(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activas: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[SedeResponse]:
	log_event("CATALOG", "LIST_SEDES", "debug", f"Listar sedes skip={skip} limit={limit}")
	return crud.get_sedes(db, skip=skip, limit=limit, solo_activas=solo_activas)


@app.get("/sedes/{sede_id}", response_model=SedeResponse, tags=["Sedes"])
def obtener_sede(sede_id: UUID, db: Session = Depends(get_db)) -> SedeResponse:
	log_event("CATALOG", "GET_SEDE", "debug", f"Obtener sede={sede_id}")
	sede = crud.get_sede_by_id(db, sede_id)
	if sede is None:
		log_event("CATALOG", "GET_SEDE", "warning", f"Sede no encontrada: {sede_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
	return sede


@app.put("/sedes/{sede_id}", response_model=SedeResponse, tags=["Sedes"])
def actualizar_sede(
	sede_id: UUID,
	payload: SedeUpdate,
	db: Session = Depends(get_db),
) -> SedeResponse:
	log_event("CATALOG", "UPDATE_SEDE", "info", f"Actualizar sede={sede_id}")
	try:
		sede = crud.update_sede(db, sede_id, payload)
		log_event("CATALOG", "UPDATE_SEDE", "info", f"Sede actualizada: {sede_id}")
		return sede
	except ValueError as exc:
		log_event("CATALOG", "UPDATE_SEDE", "warning", f"Error actualizando sede {sede_id}: {exc}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/sedes/{sede_id}", tags=["Sedes"])
def eliminar_sede(sede_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	log_event("CATALOG", "DELETE_SEDE", "info", f"Eliminar sede={sede_id}")
	deleted = crud.delete_sede(db, sede_id)
	if not deleted:
		log_event("CATALOG", "DELETE_SEDE", "warning", f"Sede no encontrada: {sede_id}")
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
	return {"success": True}


# DISPONIBILIDAD
@app.post(
	"/disponibilidades",
	response_model=DisponibilidadResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Disponibilidad"],
)
def crear_disponibilidad(
	payload: DisponibilidadCreate, db: Session = Depends(get_db)
) -> DisponibilidadResponse:
	log_event("CATALOG", "CREATE_DISP", "info", f"Crear disponibilidad medico={payload.medico_id}, dia={payload.dia_semana}")
	try:
		disp = crud.create_disponibilidad(db, payload)
		log_event("CATALOG", "CREATE_DISP", "info", f"Disponibilidad creada: {disp.disponibilidad_id}")
		return disp
	except ValueError as exc:
		log_event("CATALOG", "CREATE_DISP", "warning", f"Error creando disponibilidad: {exc}")
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get(
	"/disponibilidades/medico/{medico_id}",
	response_model=list[DisponibilidadResponse],
	tags=["Disponibilidad"],
)
def listar_disponibilidades_medico(
	medico_id: UUID,
	dia_semana: int | None = Query(default=None, ge=1, le=7),
	db: Session = Depends(get_db),
) -> list[DisponibilidadResponse]:
	log_event("CATALOG", "LIST_DISP_MED", "debug", f"Disponibilidades medico={medico_id}, dia={dia_semana}")
	return crud.get_disponibilidades_by_medico(db, medico_id=medico_id, dia_semana=dia_semana)


@app.get(
	"/disponibilidades/{disponibilidad_id}",
	response_model=DisponibilidadResponse,
	tags=["Disponibilidad"],
)
def obtener_disponibilidad(
	disponibilidad_id: UUID, db: Session = Depends(get_db)
) -> DisponibilidadResponse:
	log_event("CATALOG", "GET_DISP", "debug", f"Obtener disponibilidad={disponibilidad_id}")
	disponibilidad = crud.get_disponibilidad_by_id(db, disponibilidad_id)
	if disponibilidad is None:
		log_event("CATALOG", "GET_DISP", "warning", f"Disponibilidad no encontrada: {disponibilidad_id}")
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail="Disponibilidad no encontrada"
		)
	return disponibilidad


@app.put(
	"/disponibilidades/{disponibilidad_id}",
	response_model=DisponibilidadResponse,
	tags=["Disponibilidad"],
)
def actualizar_disponibilidad(
	disponibilidad_id: UUID,
	payload: DisponibilidadUpdate,
	db: Session = Depends(get_db),
) -> DisponibilidadResponse:
	log_event("CATALOG", "UPDATE_DISP", "info", f"Actualizar disponibilidad={disponibilidad_id}")
	try:
		disp = crud.update_disponibilidad(db, disponibilidad_id, payload)
		log_event("CATALOG", "UPDATE_DISP", "info", f"Disponibilidad actualizada: {disponibilidad_id}")
		return disp
	except ValueError as exc:
		log_event("CATALOG", "UPDATE_DISP", "warning", f"Error actualizando disponibilidad {disponibilidad_id}: {exc}")
		msg = str(exc)
		code = status.HTTP_404_NOT_FOUND if "no encontrada" in msg else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=code, detail=msg) from exc


@app.delete("/disponibilidades/{disponibilidad_id}", tags=["Disponibilidad"])
def eliminar_disponibilidad(
	disponibilidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	log_event("CATALOG", "DELETE_DISP", "info", f"Eliminar disponibilidad={disponibilidad_id}")
	deleted = crud.delete_disponibilidad(db, disponibilidad_id)
	if not deleted:
		log_event("CATALOG", "DELETE_DISP", "warning", f"Disponibilidad no encontrada: {disponibilidad_id}")
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND, detail="Disponibilidad no encontrada"
		)
	return {"success": True}


@app.get("/disponibilidades/verificar", tags=["Disponibilidad"])
def validar_disponibilidad_medico(
	medico_id: UUID,
	fecha: date,
	hora_inicio: time,
	hora_fin: time,
	db: Session = Depends(get_db),
) -> dict[str, bool]:
	log_event("CATALOG", "VERIFY_DISP", "info", f"Verificar disponibilidad medico={medico_id}, fecha={fecha}")
	disponible = crud.verificar_disponibilidad(
		db,
		medico_id=medico_id,
		fecha=fecha,
		hora_inicio=hora_inicio,
		hora_fin=hora_fin,
	)
	log_event("CATALOG", "VERIFY_DISP", "info", f"Disponibilidad={disponible} para medico={medico_id}")
	return {"disponible": disponible}


@app.get("/medicos/con-especialidades", tags=["Medicos"])
def listar_medicos_con_especialidades(
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[dict]:
	"""Lista medicos con sus especialidades incluidas en una sola respuesta."""
	log_event("CATALOG", "MEDICOS_CON_ESP", "debug", "Listar medicos con especialidades")
	return crud.get_medicos_con_especialidades(db, solo_activos=solo_activos)
