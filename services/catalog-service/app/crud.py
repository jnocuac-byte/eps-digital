from __future__ import annotations

from datetime import date, time
from importlib import import_module
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

try:
	_models = import_module("app.models")
	_schemas = import_module("app.schemas")
except ModuleNotFoundError:
	# Permite ejecucion local cuando el cwd es app/.
	_models = import_module("models")
	_schemas = import_module("schemas")

Disponibilidad = _models.Disponibilidad
Especialidad = _models.Especialidad
Medico = _models.Medico
MedicoEspecialidad = _models.MedicoEspecialidad
Sede = _models.Sede
Servicio = _models.Servicio

DisponibilidadCreate = _schemas.DisponibilidadCreate
DisponibilidadUpdate = _schemas.DisponibilidadUpdate
EspecialidadCreate = _schemas.EspecialidadCreate
EspecialidadUpdate = _schemas.EspecialidadUpdate
MedicoCreate = _schemas.MedicoCreate
MedicoUpdate = _schemas.MedicoUpdate
SedeCreate = _schemas.SedeCreate
SedeUpdate = _schemas.SedeUpdate
ServicioCreate = _schemas.ServicioCreate
ServicioUpdate = _schemas.ServicioUpdate


def _apply_updates(instance: object, data: dict) -> None:
	"""Aplica actualizaciones parciales sobre una instancia ORM."""
	for key, value in data.items():
		setattr(instance, key, value)


def _ensure_exists(db: Session, model, model_id_name: str, model_id: UUID):
	"""Valida que una entidad exista antes de relacionarla."""
	entity = db.scalar(select(model).where(getattr(model, model_id_name) == model_id))
	if entity is None:
		raise ValueError(f"{model.__name__} no encontrado")
	return entity


# SERVICIO
def create_servicio(db: Session, servicio_data: ServicioCreate) -> Servicio:
	"""Crea un servicio de catalogo."""
	servicio = Servicio(**servicio_data.model_dump())
	db.add(servicio)
	db.commit()
	db.refresh(servicio)
	return servicio


def get_servicios(
	db: Session, skip: int = 0, limit: int = 100, solo_activos: bool = True
) -> list[Servicio]:
	"""Lista servicios con paginacion y filtro por estado."""
	stmt = select(Servicio)
	if solo_activos:
		stmt = stmt.where(Servicio.activo.is_(True))
	stmt = stmt.offset(skip).limit(limit)
	return list(db.scalars(stmt).all())


def get_servicio_by_id(db: Session, servicio_id: UUID) -> Servicio | None:
	"""Obtiene un servicio por su identificador."""
	return db.scalar(select(Servicio).where(Servicio.servicio_id == servicio_id))


def update_servicio(
	db: Session, servicio_id: UUID, servicio_data: ServicioUpdate
) -> Servicio:
	"""Actualiza parcialmente un servicio."""
	servicio = get_servicio_by_id(db, servicio_id)
	if servicio is None:
		raise ValueError("Servicio no encontrado")

	updates = servicio_data.model_dump(exclude_unset=True)
	_apply_updates(servicio, updates)
	db.commit()
	db.refresh(servicio)
	return servicio


def delete_servicio(db: Session, servicio_id: UUID) -> bool:
	"""Realiza borrado logico de un servicio."""
	servicio = get_servicio_by_id(db, servicio_id)
	if servicio is None:
		return False
	servicio.activo = False
	db.commit()
	return True


# ESPECIALIDAD
def create_especialidad(db: Session, especialidad_data: EspecialidadCreate) -> Especialidad:
	"""Crea una especialidad asociada a un servicio."""
	_ensure_exists(db, Servicio, "servicio_id", especialidad_data.servicio_id)
	especialidad = Especialidad(**especialidad_data.model_dump())
	db.add(especialidad)
	db.commit()
	db.refresh(especialidad)
	return especialidad


def get_especialidades_by_servicio(
	db: Session, servicio_id: UUID, solo_activos: bool = True
) -> list[Especialidad]:
	"""Lista especialidades por servicio."""
	stmt = select(Especialidad).where(Especialidad.servicio_id == servicio_id)
	if solo_activos:
		stmt = stmt.where(Especialidad.activo.is_(True))
	return list(db.scalars(stmt).all())


def get_especialidades(
	db: Session, servicio_id: UUID | None = None, solo_activos: bool = True
) -> list[Especialidad]:
	"""Lista especialidades, con filtro opcional por servicio."""
	stmt = select(Especialidad)
	if servicio_id is not None:
		stmt = stmt.where(Especialidad.servicio_id == servicio_id)
	if solo_activos:
		stmt = stmt.where(Especialidad.activo.is_(True))
	return list(db.scalars(stmt).all())


def get_especialidad_by_id(db: Session, especialidad_id: UUID) -> Especialidad | None:
	"""Obtiene una especialidad por identificador."""
	return db.scalar(
		select(Especialidad).where(Especialidad.especialidad_id == especialidad_id)
	)


def update_especialidad(
	db: Session, especialidad_id: UUID, especialidad_data: EspecialidadUpdate
) -> Especialidad:
	"""Actualiza parcialmente una especialidad."""
	especialidad = get_especialidad_by_id(db, especialidad_id)
	if especialidad is None:
		raise ValueError("Especialidad no encontrada")

	updates = especialidad_data.model_dump(exclude_unset=True)
	if "servicio_id" in updates and updates["servicio_id"] is not None:
		_ensure_exists(db, Servicio, "servicio_id", updates["servicio_id"])

	_apply_updates(especialidad, updates)
	db.commit()
	db.refresh(especialidad)
	return especialidad


def delete_especialidad(db: Session, especialidad_id: UUID) -> bool:
	"""Realiza borrado logico de una especialidad."""
	especialidad = get_especialidad_by_id(db, especialidad_id)
	if especialidad is None:
		return False
	especialidad.activo = False
	db.commit()
	return True


# MEDICO
def create_medico(db: Session, medico_data: MedicoCreate) -> Medico:
	"""Crea un medico."""
	medico = Medico(**medico_data.model_dump())
	db.add(medico)
	db.commit()
	db.refresh(medico)
	return medico


def get_medicos(
	db: Session, skip: int = 0, limit: int = 100, solo_activos: bool = True
) -> list[Medico]:
	"""Lista medicos con paginacion y filtro por estado."""
	stmt = select(Medico)
	if solo_activos:
		stmt = stmt.where(Medico.activo.is_(True))
	stmt = stmt.offset(skip).limit(limit)
	return list(db.scalars(stmt).all())


def get_medico_by_id(db: Session, medico_id: UUID) -> Medico | None:
	"""Obtiene un medico por identificador."""
	return db.scalar(select(Medico).where(Medico.medico_id == medico_id))


def get_medico_by_registro(db: Session, numero_registro: str) -> Medico | None:
	"""Obtiene un medico por su numero de registro."""
	return db.scalar(select(Medico).where(Medico.numero_registro == numero_registro))


def update_medico(db: Session, medico_id: UUID, medico_data: MedicoUpdate) -> Medico:
	"""Actualiza parcialmente un medico."""
	medico = get_medico_by_id(db, medico_id)
	if medico is None:
		raise ValueError("Medico no encontrado")

	updates = medico_data.model_dump(exclude_unset=True)
	_apply_updates(medico, updates)
	db.commit()
	db.refresh(medico)
	return medico


def delete_medico(db: Session, medico_id: UUID) -> bool:
	"""Realiza borrado logico de un medico."""
	medico = get_medico_by_id(db, medico_id)
	if medico is None:
		return False
	medico.activo = False
	db.commit()
	return True


# MEDICO_ESPECIALIDAD
def assign_especialidad_to_medico(
	db: Session, medico_id: UUID, especialidad_id: UUID, es_principal: bool = False
) -> MedicoEspecialidad:
	"""Asigna una especialidad a un medico."""
	_ensure_exists(db, Medico, "medico_id", medico_id)
	_ensure_exists(db, Especialidad, "especialidad_id", especialidad_id)

	existente = db.scalar(
		select(MedicoEspecialidad).where(
			MedicoEspecialidad.medico_id == medico_id,
			MedicoEspecialidad.especialidad_id == especialidad_id,
		)
	)

	if existente is not None:
		if es_principal:
			for asignacion in db.scalars(
				select(MedicoEspecialidad).where(MedicoEspecialidad.medico_id == medico_id)
			).all():
				asignacion.es_principal = asignacion.medico_especialidad_id == existente.medico_especialidad_id
			db.commit()
			db.refresh(existente)
		return existente

	if es_principal:
		for asignacion in db.scalars(
			select(MedicoEspecialidad).where(MedicoEspecialidad.medico_id == medico_id)
		).all():
			asignacion.es_principal = False

	asignacion = MedicoEspecialidad(
		medico_id=medico_id,
		especialidad_id=especialidad_id,
		es_principal=es_principal,
	)
	db.add(asignacion)
	db.commit()
	db.refresh(asignacion)
	return asignacion


def remove_especialidad_from_medico(db: Session, medico_especialidad_id: UUID) -> bool:
	"""Elimina una asignacion medico-especialidad."""
	asignacion = db.scalar(
		select(MedicoEspecialidad).where(
			MedicoEspecialidad.medico_especialidad_id == medico_especialidad_id
		)
	)
	if asignacion is None:
		return False
	db.delete(asignacion)
	db.commit()
	return True


def get_medico_especialidades(db: Session, medico_id: UUID) -> list[MedicoEspecialidad]:
	"""Lista especialidades asignadas a un medico."""
	stmt = select(MedicoEspecialidad).where(MedicoEspecialidad.medico_id == medico_id)
	return list(db.scalars(stmt).all())


def get_especialidad_medicos(
	db: Session, especialidad_id: UUID
) -> list[MedicoEspecialidad]:
	"""Lista medicos asignados a una especialidad."""
	stmt = select(MedicoEspecialidad).where(
		MedicoEspecialidad.especialidad_id == especialidad_id
	)
	return list(db.scalars(stmt).all())


# SEDE
def create_sede(db: Session, sede_data: SedeCreate) -> Sede:
	"""Crea una sede."""
	sede = Sede(**sede_data.model_dump())
	db.add(sede)
	db.commit()
	db.refresh(sede)
	return sede


def get_sedes(
	db: Session, skip: int = 0, limit: int = 100, solo_activas: bool = True
) -> list[Sede]:
	"""Lista sedes con paginacion y filtro por estado."""
	stmt = select(Sede)
	if solo_activas:
		stmt = stmt.where(Sede.activo.is_(True))
	stmt = stmt.offset(skip).limit(limit)
	return list(db.scalars(stmt).all())


def get_sede_by_id(db: Session, sede_id: UUID) -> Sede | None:
	"""Obtiene una sede por identificador."""
	return db.scalar(select(Sede).where(Sede.sede_id == sede_id))


def update_sede(db: Session, sede_id: UUID, sede_data: SedeUpdate) -> Sede:
	"""Actualiza parcialmente una sede."""
	sede = get_sede_by_id(db, sede_id)
	if sede is None:
		raise ValueError("Sede no encontrada")

	updates = sede_data.model_dump(exclude_unset=True)
	_apply_updates(sede, updates)
	db.commit()
	db.refresh(sede)
	return sede


def delete_sede(db: Session, sede_id: UUID) -> bool:
	"""Realiza borrado logico de una sede."""
	sede = get_sede_by_id(db, sede_id)
	if sede is None:
		return False
	sede.activo = False
	db.commit()
	return True


# DISPONIBILIDAD
def create_disponibilidad(
	db: Session, disponibilidad_data: DisponibilidadCreate
) -> Disponibilidad:
	"""Crea una disponibilidad semanal para un medico."""
	_ensure_exists(db, Medico, "medico_id", disponibilidad_data.medico_id)
	_ensure_exists(db, Especialidad, "especialidad_id", disponibilidad_data.especialidad_id)
	_ensure_exists(db, Sede, "sede_id", disponibilidad_data.sede_id)

	# Evita cruces de horarios para el mismo medico y dia.
	cruce = db.scalar(
		select(Disponibilidad).where(
			Disponibilidad.medico_id == disponibilidad_data.medico_id,
			Disponibilidad.dia_semana == disponibilidad_data.dia_semana,
			Disponibilidad.activo.is_(True),
			Disponibilidad.hora_inicio < disponibilidad_data.hora_fin,
			Disponibilidad.hora_fin > disponibilidad_data.hora_inicio,
		)
	)
	if cruce is not None:
		raise ValueError("Existe un cruce de horario para el medico en ese dia")

	disponibilidad = Disponibilidad(**disponibilidad_data.model_dump())
	db.add(disponibilidad)
	db.commit()
	db.refresh(disponibilidad)
	return disponibilidad


def get_disponibilidades_by_medico(
	db: Session, medico_id: UUID, dia_semana: int | None = None
) -> list[Disponibilidad]:
	"""Lista disponibilidades activas de un medico, opcionalmente por dia."""
	stmt = select(Disponibilidad).where(
		Disponibilidad.medico_id == medico_id,
		Disponibilidad.activo.is_(True),
	)
	if dia_semana is not None:
		stmt = stmt.where(Disponibilidad.dia_semana == dia_semana)
	return list(db.scalars(stmt).all())


def get_disponibilidad_by_id(db: Session, disponibilidad_id: UUID) -> Disponibilidad | None:
	"""Obtiene disponibilidad por identificador."""
	return db.scalar(
		select(Disponibilidad).where(Disponibilidad.disponibilidad_id == disponibilidad_id)
	)


def update_disponibilidad(
	db: Session, disponibilidad_id: UUID, disponibilidad_data: DisponibilidadUpdate
) -> Disponibilidad:
	"""Actualiza parcialmente una disponibilidad."""
	disponibilidad = get_disponibilidad_by_id(db, disponibilidad_id)
	if disponibilidad is None:
		raise ValueError("Disponibilidad no encontrada")

	updates = disponibilidad_data.model_dump(exclude_unset=True)

	medico_id = updates.get("medico_id", disponibilidad.medico_id)
	especialidad_id = updates.get("especialidad_id", disponibilidad.especialidad_id)
	sede_id = updates.get("sede_id", disponibilidad.sede_id)
	dia_semana = updates.get("dia_semana", disponibilidad.dia_semana)
	hora_inicio = updates.get("hora_inicio", disponibilidad.hora_inicio)
	hora_fin = updates.get("hora_fin", disponibilidad.hora_fin)

	_ensure_exists(db, Medico, "medico_id", medico_id)
	_ensure_exists(db, Especialidad, "especialidad_id", especialidad_id)
	_ensure_exists(db, Sede, "sede_id", sede_id)

	if hora_fin <= hora_inicio:
		raise ValueError("hora_fin debe ser mayor que hora_inicio")

	cruce = db.scalar(
		select(Disponibilidad).where(
			Disponibilidad.disponibilidad_id != disponibilidad_id,
			Disponibilidad.medico_id == medico_id,
			Disponibilidad.dia_semana == dia_semana,
			Disponibilidad.activo.is_(True),
			Disponibilidad.hora_inicio < hora_fin,
			Disponibilidad.hora_fin > hora_inicio,
		)
	)
	if cruce is not None:
		raise ValueError("Existe un cruce de horario para el medico en ese dia")

	_apply_updates(disponibilidad, updates)
	db.commit()
	db.refresh(disponibilidad)
	return disponibilidad


def delete_disponibilidad(db: Session, disponibilidad_id: UUID) -> bool:
	"""Realiza borrado logico de una disponibilidad."""
	disponibilidad = get_disponibilidad_by_id(db, disponibilidad_id)
	if disponibilidad is None:
		return False
	disponibilidad.activo = False
	db.commit()
	return True


def verificar_disponibilidad(
	db: Session,
	medico_id: UUID,
	fecha: date,
	hora_inicio: time,
	hora_fin: time,
) -> bool:
	"""Verifica si un medico tiene disponibilidad activa para una fecha y rango horario."""
	if hora_fin <= hora_inicio:
		return False

	dia_semana = fecha.isoweekday()

	disponible = db.scalar(
		select(Disponibilidad).where(
			Disponibilidad.medico_id == medico_id,
			Disponibilidad.dia_semana == dia_semana,
			Disponibilidad.activo.is_(True),
			Disponibilidad.hora_inicio <= hora_inicio,
			Disponibilidad.hora_fin >= hora_fin,
		)
	)
	return disponible is not None
