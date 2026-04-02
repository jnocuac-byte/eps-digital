from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Afiliacion, InformacionMedica, Usuario
from app.schemas import AfiliacionCreate, MedicalInfoCreate, UserCreate, UserUpdate


def get_user_by_id(db: Session, usuario_id: UUID) -> Usuario | None:
	"""Obtiene un usuario por su identificador unico."""
	stmt = select(Usuario).where(Usuario.usuario_id == usuario_id)
	return db.scalar(stmt)


def get_user_by_documento(db: Session, numero_documento: str) -> Usuario | None:
	"""Obtiene un usuario por numero de documento."""
	stmt = select(Usuario).where(Usuario.numero_documento == numero_documento)
	return db.scalar(stmt)


def get_user_by_correo(db: Session, correo: str) -> Usuario | None:
	"""Obtiene un usuario por correo electronico."""
	stmt = select(Usuario).where(Usuario.correo == correo)
	return db.scalar(stmt)


def create_user(db: Session, user_data: UserCreate) -> Usuario:
	"""Crea un usuario nuevo validando duplicados de identificadores unicos."""
	if get_user_by_id(db, user_data.usuario_id):
		raise ValueError(f"Ya existe un usuario con usuario_id {user_data.usuario_id}")

	if get_user_by_documento(db, user_data.numero_documento):
		raise ValueError(f"Ya existe un usuario con numero_documento {user_data.numero_documento}")

	if get_user_by_correo(db, user_data.correo):
		raise ValueError(f"Ya existe un usuario con correo {user_data.correo}")

	nuevo_usuario = Usuario(**user_data.model_dump())
	db.add(nuevo_usuario)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo crear el usuario por conflicto de integridad") from exc

	db.refresh(nuevo_usuario)
	return nuevo_usuario


def update_user(db: Session, usuario_id: UUID, user_data: UserUpdate) -> Usuario:
	"""Actualiza datos personales del usuario solo con campos enviados y no nulos."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise ValueError(f"No existe usuario con id {usuario_id}")

	# Solo se aplican cambios con valor real para evitar sobreescribir con None.
	update_data = user_data.model_dump(exclude_unset=True, exclude_none=True)
	if not update_data:
		return usuario

	if "numero_documento" in update_data:
		existente_documento = get_user_by_documento(db, update_data["numero_documento"])
		if existente_documento and existente_documento.usuario_id != usuario_id:
			raise ValueError(
				f"El numero_documento {update_data['numero_documento']} ya esta en uso"
			)

	if "correo" in update_data:
		existente_correo = get_user_by_correo(db, update_data["correo"])
		if existente_correo and existente_correo.usuario_id != usuario_id:
			raise ValueError(f"El correo {update_data['correo']} ya esta en uso")

	for field_name, value in update_data.items():
		setattr(usuario, field_name, value)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo actualizar el usuario por conflicto de integridad") from exc

	db.refresh(usuario)
	return usuario


def delete_user(db: Session, usuario_id: UUID) -> bool:
	"""Elimina un usuario de forma permanente (hard delete)."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise ValueError(f"No existe usuario con id {usuario_id}")

	db.delete(usuario)
	db.commit()
	return True


def get_medical_info(db: Session, usuario_id: UUID) -> InformacionMedica | None:
	"""Obtiene la informacion medica asociada a un usuario."""
	stmt = select(InformacionMedica).where(InformacionMedica.usuario_id == usuario_id)
	return db.scalar(stmt)


def create_or_update_medical_info(
	db: Session, usuario_id: UUID, info_data: MedicalInfoCreate
) -> InformacionMedica:
	"""Crea o actualiza la informacion medica 1:1 de un usuario."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise ValueError(f"No existe usuario con id {usuario_id}")

	info_medica = get_medical_info(db, usuario_id)
	data = info_data.model_dump()

	if info_medica:
		for field_name, value in data.items():
			setattr(info_medica, field_name, value)
	else:
		info_medica = InformacionMedica(usuario_id=usuario_id, **data)
		db.add(info_medica)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo guardar la informacion medica por conflicto de integridad") from exc

	db.refresh(info_medica)
	return info_medica


def get_afiliacion(db: Session, usuario_id: UUID) -> Afiliacion | None:
	"""Obtiene la afiliacion asociada a un usuario."""
	stmt = select(Afiliacion).where(Afiliacion.usuario_id == usuario_id)
	return db.scalar(stmt)


def create_afiliacion(db: Session, usuario_id: UUID, afiliacion_data: AfiliacionCreate) -> Afiliacion:
	"""Crea la afiliacion 1:1 de un usuario."""
	usuario = get_user_by_id(db, usuario_id)
	if not usuario:
		raise ValueError(f"No existe usuario con id {usuario_id}")

	afiliacion_existente = get_afiliacion(db, usuario_id)
	if afiliacion_existente:
		raise ValueError(f"El usuario {usuario_id} ya tiene una afiliacion registrada")

	nueva_afiliacion = Afiliacion(usuario_id=usuario_id, **afiliacion_data.model_dump())
	db.add(nueva_afiliacion)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo crear la afiliacion por conflicto de integridad") from exc

	db.refresh(nueva_afiliacion)
	return nueva_afiliacion


def update_afiliacion_estado(db: Session, usuario_id: UUID, estado: str) -> Afiliacion:
	"""Actualiza solo el estado de la afiliacion del usuario."""
	afiliacion = get_afiliacion(db, usuario_id)
	if not afiliacion:
		raise ValueError(f"No existe afiliacion para el usuario {usuario_id}")

	nuevo_estado = estado.strip().lower()
	if not nuevo_estado:
		raise ValueError("El estado de afiliacion no puede estar vacio")

	afiliacion.estado = nuevo_estado

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo actualizar el estado de afiliacion") from exc

	db.refresh(afiliacion)
	return afiliacion
