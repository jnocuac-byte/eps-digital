from uuid import UUID

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud import (
	create_afiliacion,
	create_or_update_medical_info,
	create_user,
	delete_user,
	get_afiliacion,
	get_medical_info,
	get_user_by_tipo_y_numero_documento,
	get_user_by_id,
	update_afiliacion_estado,
	update_user,
)
from app.database import Base, engine, get_db
from app.schemas import (
	AfiliacionCreate,
	AfiliacionResponse,
	MedicalInfoCreate,
	MedicalInfoResponse,
	UserCreate,
	UserLookupResponse,
	UserResponse,
	UserUpdate,
	UsuarioCompletoResponse,
)

from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
	title="User Service",
	description="API para gestion de perfiles de usuario, informacion medica y afiliacion.",
	version="1.0.0",
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
    allow_origin_regex="https://.*\.onrender\.com",  # Permite cualquier subdominio de onrender
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

class MessageResponse(BaseModel):
	"""Respuesta simple para operaciones de confirmacion."""

	message: str = Field(..., example="Operacion realizada correctamente")


class EstadoAfiliacionUpdate(BaseModel):
	"""Payload para actualizar el estado de la afiliacion."""

	estado: str = Field(..., min_length=1, max_length=20, example="inactivo")


def _status_from_value_error(error: ValueError, default_status: int) -> int:
	"""Mapea ValueError a codigo HTTP segun el tipo de mensaje."""
	message = str(error).lower()
	if "no existe" in message:
		return status.HTTP_404_NOT_FOUND
	return default_status


@app.post(
	"/usuarios",
	response_model=UserResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["usuarios"],
	responses={
		201: {"description": "Usuario creado correctamente"},
		400: {"description": "Datos invalidos o conflicto de unicidad"},
	},
)
def create_user_endpoint(user_data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
	"""Crea el perfil de usuario en el servicio."""
	try:
		return create_user(db, user_data)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get(
	"/usuarios/buscar",
	response_model=UserLookupResponse,
	tags=["usuarios"],
	responses={404: {"description": "Usuario no encontrado para el documento"}},
)
def buscar_usuario_por_documento_endpoint(
	tipo_documento: str = Query(..., min_length=2, max_length=5),
	numero_documento: str = Query(..., min_length=5, max_length=20),
	db: Session = Depends(get_db),
) -> UserLookupResponse:
	"""Busca un usuario por tipo y numero de documento."""
	usuario = get_user_by_tipo_y_numero_documento(db, tipo_documento, numero_documento)
	if not usuario:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Usuario no encontrado para el documento enviado",
		)

	return UserLookupResponse(
		usuario_id=usuario.usuario_id,
		correo=usuario.correo,
		nombres=usuario.nombres,
		apellidos=usuario.apellidos,
	)


@app.get(
	"/usuarios/{usuario_id}",
	response_model=UserResponse,
	tags=["usuarios"],
	responses={404: {"description": "Usuario no encontrado"}},
)
def get_user_endpoint(usuario_id: UUID, db: Session = Depends(get_db)) -> UserResponse:
	"""Consulta un usuario por su identificador."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
	return usuario


@app.put(
	"/usuarios/{usuario_id}",
	response_model=UserResponse,
	tags=["usuarios"],
	responses={
		400: {"description": "Datos invalidos o conflicto"},
		404: {"description": "Usuario no encontrado"},
	},
)
def update_user_endpoint(
	usuario_id: UUID,
	user_data: UserUpdate,
	db: Session = Depends(get_db),
) -> UserResponse:
	"""Actualiza parcialmente los datos personales del usuario."""
	try:
		return update_user(db, usuario_id, user_data)
	except ValueError as exc:
		status_code = _status_from_value_error(exc, status.HTTP_400_BAD_REQUEST)
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.delete(
	"/usuarios/{usuario_id}",
	response_model=MessageResponse,
	tags=["usuarios"],
	responses={404: {"description": "Usuario no encontrado"}},
)
def delete_user_endpoint(usuario_id: UUID, db: Session = Depends(get_db)) -> MessageResponse:
	"""Elimina un usuario de forma permanente."""
	try:
		delete_user(db, usuario_id)
		return MessageResponse(message="Usuario eliminado correctamente")
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get(
	"/usuarios/{usuario_id}/medica",
	response_model=MedicalInfoResponse | None,
	tags=["usuarios"],
	responses={200: {"description": "Informacion medica encontrada o null"}},
)
def get_medical_info_endpoint(
	usuario_id: UUID,
	db: Session = Depends(get_db),
) -> MedicalInfoResponse | None:
	"""Obtiene la informacion medica de un usuario."""
	return get_medical_info(db, usuario_id)


@app.put(
	"/usuarios/{usuario_id}/medica",
	response_model=MedicalInfoResponse,
	tags=["usuarios"],
	responses={404: {"description": "Usuario no encontrado"}},
)
def upsert_medical_info_endpoint(
	usuario_id: UUID,
	info_data: MedicalInfoCreate,
	db: Session = Depends(get_db),
) -> MedicalInfoResponse:
	"""Crea o actualiza la informacion medica del usuario."""
	try:
		return create_or_update_medical_info(db, usuario_id, info_data)
	except ValueError as exc:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get(
	"/usuarios/{usuario_id}/afiliacion",
	response_model=AfiliacionResponse | None,
	tags=["usuarios"],
	responses={200: {"description": "Afiliacion encontrada o null"}},
)
def get_afiliacion_endpoint(usuario_id: UUID, db: Session = Depends(get_db)) -> AfiliacionResponse | None:
	"""Obtiene la afiliacion de un usuario."""
	return get_afiliacion(db, usuario_id)


@app.post(
	"/usuarios/{usuario_id}/afiliacion",
	response_model=AfiliacionResponse,
	status_code=status.HTTP_201_CREATED,
	tags=["usuarios"],
	responses={
		400: {"description": "Conflicto de afiliacion o datos invalidos"},
		404: {"description": "Usuario no encontrado"},
	},
)
def create_afiliacion_endpoint(
	usuario_id: UUID,
	afiliacion_data: AfiliacionCreate,
	db: Session = Depends(get_db),
) -> AfiliacionResponse:
	"""Crea la afiliacion del usuario."""
	try:
		return create_afiliacion(db, usuario_id, afiliacion_data)
	except ValueError as exc:
		status_code = _status_from_value_error(exc, status.HTTP_400_BAD_REQUEST)
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.patch(
	"/usuarios/{usuario_id}/afiliacion/estado",
	response_model=AfiliacionResponse,
	tags=["usuarios"],
	responses={
		400: {"description": "Estado invalido"},
		404: {"description": "Afiliacion no encontrada"},
	},
)
def update_afiliacion_estado_endpoint(
	usuario_id: UUID,
	payload: EstadoAfiliacionUpdate,
	db: Session = Depends(get_db),
) -> AfiliacionResponse:
	"""Actualiza el estado de la afiliacion de un usuario."""
	try:
		return update_afiliacion_estado(db, usuario_id, payload.estado)
	except ValueError as exc:
		status_code = _status_from_value_error(exc, status.HTTP_400_BAD_REQUEST)
		raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@app.get(
	"/usuarios/{usuario_id}/completo",
	response_model=UsuarioCompletoResponse,
	tags=["usuarios"],
	responses={404: {"description": "Usuario no encontrado"}},
)
def get_usuario_completo_endpoint(
	usuario_id: UUID,
	db: Session = Depends(get_db),
) -> UsuarioCompletoResponse:
	"""Retorna perfil completo de usuario con secciones medica y afiliacion."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

	informacion_medica = get_medical_info(db, usuario_id)
	afiliacion = get_afiliacion(db, usuario_id)

	return UsuarioCompletoResponse(
		user=usuario,
		informacion_medica=informacion_medica,
		afiliacion=afiliacion,
	)
