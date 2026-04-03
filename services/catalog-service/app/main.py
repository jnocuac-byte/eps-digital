from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, time
from importlib import import_module
from uuid import UUID

from requests import Request, Response

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
	Base.metadata.create_all(bind=engine)
	yield


app = FastAPI(
	title="EPS Digital - Catalogo Service",
	version="1.0.0",
	description="Servicio de catalogo medico para servicios, especialidades y disponibilidad.",
	lifespan=lifespan,
)

origins = [
    "https://eps-digital-cn2h.onrender.com",
    "https://eps-digital-cn2h.onrender.com/",  # Con slash también por si acaso
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5173/",
    "http://127.0.0.1:5173/",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.onrender\.com",  # Permite cualquier subdominio de onrender
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
	max_age=600,
)

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request) -> Response:
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "https://eps-digital-cn2h.onrender.com"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

# SERVICIOS
@app.post(
	"/servicios",
	response_model=ServicioResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Servicios"],
)
def crear_servicio(payload: ServicioCreate, db: Session = Depends(get_db)) -> ServicioResponse:
	try:
		return crud.create_servicio(db, payload)
	except Exception as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/servicios", response_model=list[ServicioResponse], tags=["Servicios"])
def listar_servicios(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[ServicioResponse]:
	return crud.get_servicios(db, skip=skip, limit=limit, solo_activos=solo_activos)


@app.get("/servicios/{servicio_id}", response_model=ServicioResponse, tags=["Servicios"])
def obtener_servicio(servicio_id: UUID, db: Session = Depends(get_db)) -> ServicioResponse:
	servicio = crud.get_servicio_by_id(db, servicio_id)
	if servicio is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Servicio no encontrado")
	return servicio


@app.put("/servicios/{servicio_id}", response_model=ServicioResponse, tags=["Servicios"])
def actualizar_servicio(
	servicio_id: UUID,
	payload: ServicioUpdate,
	db: Session = Depends(get_db),
) -> ServicioResponse:
	try:
		return crud.update_servicio(db, servicio_id, payload)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/servicios/{servicio_id}", tags=["Servicios"])
def eliminar_servicio(servicio_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	deleted = crud.delete_servicio(db, servicio_id)
	if not deleted:
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
	try:
		return crud.create_especialidad(db, payload)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/especialidades", response_model=list[EspecialidadResponse], tags=["Especialidades"])
def listar_especialidades(
	servicio_id: UUID | None = Query(default=None),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[EspecialidadResponse]:
	return crud.get_especialidades(db, servicio_id=servicio_id, solo_activos=solo_activos)


@app.get(
	"/especialidades/{especialidad_id}",
	response_model=EspecialidadResponse,
	tags=["Especialidades"],
)
def obtener_especialidad(especialidad_id: UUID, db: Session = Depends(get_db)) -> EspecialidadResponse:
	especialidad = crud.get_especialidad_by_id(db, especialidad_id)
	if especialidad is None:
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
	try:
		return crud.update_especialidad(db, especialidad_id, payload)
	except ValueError as exc:
		msg = str(exc)
		code = status.HTTP_404_NOT_FOUND if "no encontrada" in msg else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=code, detail=msg) from exc


@app.delete("/especialidades/{especialidad_id}", tags=["Especialidades"])
def eliminar_especialidad(
	especialidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	deleted = crud.delete_especialidad(db, especialidad_id)
	if not deleted:
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
	try:
		return crud.create_medico(db, payload)
	except Exception as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/medicos", response_model=list[MedicoResponse], tags=["Medicos"])
def listar_medicos(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activos: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[MedicoResponse]:
	return crud.get_medicos(db, skip=skip, limit=limit, solo_activos=solo_activos)


@app.get(
	"/medicos/registro/{numero_registro}",
	response_model=MedicoResponse,
	tags=["Medicos"],
)
def obtener_medico_por_registro(
	numero_registro: str, db: Session = Depends(get_db)
) -> MedicoResponse:
	medico = crud.get_medico_by_registro(db, numero_registro)
	if medico is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
	return medico


@app.get("/medicos/{medico_id}", response_model=MedicoResponse, tags=["Medicos"])
def obtener_medico(medico_id: UUID, db: Session = Depends(get_db)) -> MedicoResponse:
	medico = crud.get_medico_by_id(db, medico_id)
	if medico is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Medico no encontrado")
	return medico


@app.put("/medicos/{medico_id}", response_model=MedicoResponse, tags=["Medicos"])
def actualizar_medico(
	medico_id: UUID,
	payload: MedicoUpdate,
	db: Session = Depends(get_db),
) -> MedicoResponse:
	try:
		return crud.update_medico(db, medico_id, payload)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/medicos/{medico_id}", tags=["Medicos"])
def eliminar_medico(medico_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	deleted = crud.delete_medico(db, medico_id)
	if not deleted:
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
	try:
		return crud.assign_especialidad_to_medico(
			db,
			medico_id=medico_id,
			especialidad_id=especialidad_id,
			es_principal=es_principal,
		)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete(
	"/medico-especialidades/{medico_especialidad_id}",
	tags=["Medico-Especialidad"],
)
def remover_especialidad_medico(
	medico_especialidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	deleted = crud.remove_especialidad_from_medico(db, medico_especialidad_id)
	if not deleted:
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
	return crud.get_medico_especialidades(db, medico_id)


@app.get(
	"/especialidades/{especialidad_id}/medicos",
	response_model=list[MedicoEspecialidadResponse],
	tags=["Medico-Especialidad"],
)
def listar_medicos_especialidad(
	especialidad_id: UUID, db: Session = Depends(get_db)
) -> list[MedicoEspecialidadResponse]:
	return crud.get_especialidad_medicos(db, especialidad_id)


# SEDES
@app.post(
	"/sedes",
	response_model=SedeResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["Sedes"],
)
def crear_sede(payload: SedeCreate, db: Session = Depends(get_db)) -> SedeResponse:
	try:
		return crud.create_sede(db, payload)
	except Exception as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/sedes", response_model=list[SedeResponse], tags=["Sedes"])
def listar_sedes(
	skip: int = Query(default=0, ge=0),
	limit: int = Query(default=100, ge=1, le=500),
	solo_activas: bool = Query(default=True),
	db: Session = Depends(get_db),
) -> list[SedeResponse]:
	return crud.get_sedes(db, skip=skip, limit=limit, solo_activas=solo_activas)


@app.get("/sedes/{sede_id}", response_model=SedeResponse, tags=["Sedes"])
def obtener_sede(sede_id: UUID, db: Session = Depends(get_db)) -> SedeResponse:
	sede = crud.get_sede_by_id(db, sede_id)
	if sede is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sede no encontrada")
	return sede


@app.put("/sedes/{sede_id}", response_model=SedeResponse, tags=["Sedes"])
def actualizar_sede(
	sede_id: UUID,
	payload: SedeUpdate,
	db: Session = Depends(get_db),
) -> SedeResponse:
	try:
		return crud.update_sede(db, sede_id, payload)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete("/sedes/{sede_id}", tags=["Sedes"])
def eliminar_sede(sede_id: UUID, db: Session = Depends(get_db)) -> dict[str, bool]:
	deleted = crud.delete_sede(db, sede_id)
	if not deleted:
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
	try:
		return crud.create_disponibilidad(db, payload)
	except ValueError as exc:
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
	return crud.get_disponibilidades_by_medico(db, medico_id=medico_id, dia_semana=dia_semana)


@app.get(
	"/disponibilidades/{disponibilidad_id}",
	response_model=DisponibilidadResponse,
	tags=["Disponibilidad"],
)
def obtener_disponibilidad(
	disponibilidad_id: UUID, db: Session = Depends(get_db)
) -> DisponibilidadResponse:
	disponibilidad = crud.get_disponibilidad_by_id(db, disponibilidad_id)
	if disponibilidad is None:
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
	try:
		return crud.update_disponibilidad(db, disponibilidad_id, payload)
	except ValueError as exc:
		msg = str(exc)
		code = status.HTTP_404_NOT_FOUND if "no encontrada" in msg else status.HTTP_400_BAD_REQUEST
		raise HTTPException(status_code=code, detail=msg) from exc


@app.delete("/disponibilidades/{disponibilidad_id}", tags=["Disponibilidad"])
def eliminar_disponibilidad(
	disponibilidad_id: UUID, db: Session = Depends(get_db)
) -> dict[str, bool]:
	deleted = crud.delete_disponibilidad(db, disponibilidad_id)
	if not deleted:
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
	disponible = crud.verificar_disponibilidad(
		db,
		medico_id=medico_id,
		fecha=fecha,
		hora_inicio=hora_inicio,
		hora_fin=hora_fin,
	)
	return {"disponible": disponible}
