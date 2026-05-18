from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Cita, HistorialEstado, Recordatorio
from app.schemas import CitaCreate, CitaUpdate

CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8004")

TIPO_SERVICIO_A_SERVICIO = {
	"medicina_general": "Medicina General",
	"especialista": "Medicina Especializada",
	"urgencias": "Urgencias",
	"laboratorio": "Laboratorio",
}


def _obtener_medico_automatico(
	tipo_servicio: str,
	especialidad_id: UUID | None,
	fecha_cita: date,
	hora_inicio: time,
	hora_fin: time,
) -> UUID | None:
	"""Obtiene un medico disponible automaticamente (Round Robin)."""
	servicio_nombre = TIPO_SERVICIO_A_SERVICIO.get(tipo_servicio)
	if not servicio_nombre:
		return None

	try:
		with httpx.Client(timeout=10.0) as client:
			resp_servicios = client.get(
				f"{CATALOG_SERVICE_URL}/servicios",
				params={"solo_activos": True},
			)
			if resp_servicios.status_code != 200:
				return None
			servicios = resp_servicios.json()
			servicio_obj = next(
				(s for s in servicios if s["nombre"].lower() == servicio_nombre.lower()),
				None,
			)
			if not servicio_obj:
				return None

			servicio_id = servicio_obj["servicio_id"]

			params = {
				"servicio_id": servicio_id,
				"fecha": str(fecha_cita),
				"hora_inicio": hora_inicio.isoformat(),
				"hora_fin": hora_fin.isoformat(),
			}
			if especialidad_id:
				params["especialidad_id"] = str(especialidad_id)

			resp_medicos = client.get(
				f"{CATALOG_SERVICE_URL}/medicos/disponibles",
				params=params,
			)
			if resp_medicos.status_code != 200:
				return None
			medicos = resp_medicos.json()
			if medicos:
				return UUID(medicos[0]["medico_id"])
	except Exception:
		return None
	return None


def utc_now() -> datetime:
	"""Retorna fecha/hora actual en UTC con timezone-aware."""
	return datetime.now(timezone.utc)


def es_horario_ocupado(
	db: Session,
	medico_id: UUID,
	fecha: date,
	hora_inicio: time,
	hora_fin: time,
	excluir_cita_id: UUID | None = None,
) -> bool:
	"""Verifica si el medico ya tiene una cita programada en un rango superpuesto."""
	condiciones = [
		Cita.medico_id == medico_id,
		Cita.fecha_cita == fecha,
		Cita.estado == "programada",
		# Hay traslape cuando inicio < fin_existente y fin > inicio_existente.
		and_(Cita.hora_inicio < hora_fin, Cita.hora_fin > hora_inicio),
	]

	if excluir_cita_id is not None:
		condiciones.append(Cita.cita_id != excluir_cita_id)

	stmt = select(Cita.cita_id).where(*condiciones).limit(1)
	return db.scalar(stmt) is not None


def create_cita(db: Session, cita_data: CitaCreate) -> Cita:
	"""Crea una cita validando disponibilidad horaria del medico."""
	medico_id = cita_data.medico_id

	if medico_id is None:
		medico_id = _obtener_medico_automatico(
			tipo_servicio=cita_data.tipo_servicio,
			especialidad_id=cita_data.especialidad_id,
			fecha_cita=cita_data.fecha_cita,
			hora_inicio=cita_data.hora_inicio,
			hora_fin=cita_data.hora_fin,
		)
		if medico_id is None:
			raise ValueError(
				"No hay médicos disponibles para el servicio y horario seleccionado. "
				"Por favor selecciona un médico específico o intenta en otro horario."
			)

	if es_horario_ocupado(
		db=db,
		medico_id=medico_id,
		fecha=cita_data.fecha_cita,
		hora_inicio=cita_data.hora_inicio,
		hora_fin=cita_data.hora_fin,
	):
		raise ValueError("El medico ya tiene una cita programada en ese horario")

	cita_data.medico_id = medico_id
	nueva_cita = Cita(**cita_data.model_dump())
	db.add(nueva_cita)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError(f"No se pudo crear la cita: {exc}") from exc

	db.refresh(nueva_cita)
	return nueva_cita


def get_cita_by_id(db: Session, cita_id: UUID) -> Cita | None:
	"""Obtiene una cita por su identificador unico."""
	stmt = select(Cita).where(Cita.cita_id == cita_id)
	return db.scalar(stmt)


def get_citas_by_usuario(
	db: Session,
	usuario_id: UUID,
	skip: int = 0,
	limit: int = 100,
) -> list[Cita]:
	"""Lista citas de un usuario con paginacion basica."""
	stmt = (
		select(Cita)
		.where(Cita.usuario_id == usuario_id)
		.order_by(Cita.fecha_cita, Cita.hora_inicio)
		.offset(skip)
		.limit(limit)
	)
	return list(db.scalars(stmt).all())


def get_citas_historicas_by_usuario(
	db: Session,
	usuario_id: UUID,
	skip: int = 0,
	limit: int = 100,
) -> list[Cita]:
	"""Lista citas historicas (no programadas) de un usuario."""
	stmt = (
		select(Cita)
		.where(
			Cita.usuario_id == usuario_id,
			Cita.estado != "programada",
		)
		.order_by(Cita.fecha_cita.desc(), Cita.hora_inicio)
		.offset(skip)
		.limit(limit)
	)
	return list(db.scalars(stmt).all())


def get_citas_by_medico(
	db: Session,
	medico_id: UUID,
	fecha: date | None = None,
	fecha_inicio: date | None = None,
	fecha_fin: date | None = None,
) -> list[Cita]:
	"""Lista citas de un medico, opcionalmente filtradas por fecha o rango."""
	stmt = select(Cita).where(Cita.medico_id == medico_id)
	if fecha is not None:
		stmt = stmt.where(Cita.fecha_cita == fecha)
	elif fecha_inicio is not None or fecha_fin is not None:
		if fecha_inicio is not None:
			stmt = stmt.where(Cita.fecha_cita >= fecha_inicio)
		if fecha_fin is not None:
			stmt = stmt.where(Cita.fecha_cita <= fecha_fin)

	stmt = stmt.order_by(Cita.fecha_cita, Cita.hora_inicio)
	return list(db.scalars(stmt).all())


def get_citas_by_estado(
	db: Session,
	estado: str,
	skip: int = 0,
	limit: int = 100,
) -> list[Cita]:
	"""Lista citas por estado con paginacion basica."""
	stmt = (
		select(Cita)
		.where(Cita.estado == estado)
		.order_by(Cita.fecha_cita, Cita.hora_inicio)
		.offset(skip)
		.limit(limit)
	)
	return list(db.scalars(stmt).all())


def update_cita(db: Session, cita_id: UUID, cita_data: CitaUpdate) -> Cita:
	"""Actualiza una cita y registra historial si hay cambio de estado."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	update_data = cita_data.model_dump(exclude_unset=True, exclude_none=True)
	if not update_data:
		return cita

	# Si cambia horario/fecha en update, valida disponibilidad del medico.
	nueva_fecha = update_data.get("fecha_cita", cita.fecha_cita)
	nueva_hora_inicio = update_data.get("hora_inicio", cita.hora_inicio)
	nueva_hora_fin = update_data.get("hora_fin", cita.hora_fin)

	if (
		"fecha_cita" in update_data
		or "hora_inicio" in update_data
		or "hora_fin" in update_data
	):
		if es_horario_ocupado(
			db=db,
			medico_id=cita.medico_id,
			fecha=nueva_fecha,
			hora_inicio=nueva_hora_inicio,
			hora_fin=nueva_hora_fin,
			excluir_cita_id=cita.cita_id,
		):
			raise ValueError("El medico ya tiene una cita programada en ese horario")

	estado_anterior = cita.estado

	for field_name, value in update_data.items():
		setattr(cita, field_name, value)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo actualizar la cita por conflicto de integridad") from exc

	# Si hubo cambio de estado, registra historial en transaccion independiente.
	if "estado" in update_data and update_data["estado"] != estado_anterior:
		add_historial_estado(
			db=db,
			cita_id=cita.cita_id,
			estado_anterior=estado_anterior,
			estado_nuevo=update_data["estado"],
			motivo=None,
			realizado_por=cita.usuario_id,
		)

	db.refresh(cita)
	return cita


def cancelar_cita(db: Session, cita_id: UUID, motivo: str | None, realizado_por: UUID) -> Cita:
	"""Cancela una cita solo si esta programada y registra historial."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	if cita.estado != "programada":
		raise ValueError("Solo se puede cancelar una cita en estado 'programada'")

	estado_anterior = cita.estado
	cita.estado = "cancelada"

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo cancelar la cita") from exc

	add_historial_estado(
		db=db,
		cita_id=cita.cita_id,
		estado_anterior=estado_anterior,
		estado_nuevo="cancelada",
		motivo=motivo,
		realizado_por=realizado_por,
	)

	db.refresh(cita)
	return cita


def reprogramar_cita(
	db: Session,
	cita_id: UUID,
	nueva_fecha: date,
	nueva_hora_inicio: time,
	nueva_hora_fin: time,
	realizado_por: UUID,
) -> Cita:
	"""Reprograma una cita validando que el nuevo horario este disponible."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	if es_horario_ocupado(
		db=db,
		medico_id=cita.medico_id,
		fecha=nueva_fecha,
		hora_inicio=nueva_hora_inicio,
		hora_fin=nueva_hora_fin,
		excluir_cita_id=cita.cita_id,
	):
		raise ValueError("El medico ya tiene una cita programada en el nuevo horario")

	estado_anterior = cita.estado
	if cita.estado != "programada":
		# Al reprogramar, la cita vuelve a quedar programada.
		cita.estado = "programada"

	cita.fecha_cita = nueva_fecha
	cita.hora_inicio = nueva_hora_inicio
	cita.hora_fin = nueva_hora_fin

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo reprogramar la cita") from exc

	if cita.estado != estado_anterior:
		add_historial_estado(
			db=db,
			cita_id=cita.cita_id,
			estado_anterior=estado_anterior,
			estado_nuevo=cita.estado,
			motivo="Reprogramacion de cita",
			realizado_por=realizado_por,
		)

	db.refresh(cita)
	return cita


def delete_cita(db: Session, cita_id: UUID) -> bool:
	"""Elimina una cita de forma permanente."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	db.delete(cita)
	db.commit()
	return True


def add_historial_estado(
	db: Session,
	cita_id: UUID,
	estado_anterior: str,
	estado_nuevo: str,
	motivo: str | None,
	realizado_por: UUID,
) -> HistorialEstado:
	"""Crea un registro en el historial de cambios de estado de una cita."""
	nuevo_historial = HistorialEstado(
		cita_id=cita_id,
		estado_anterior=estado_anterior,
		estado_nuevo=estado_nuevo,
		motivo=motivo,
		realizado_por=realizado_por,
	)
	db.add(nuevo_historial)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo registrar el historial de estado") from exc

	db.refresh(nuevo_historial)
	return nuevo_historial


def get_historial_by_cita(db: Session, cita_id: UUID) -> list[HistorialEstado]:
	"""Obtiene el historial de cambios de estado de una cita ordenado por fecha."""
	stmt = (
		select(HistorialEstado)
		.where(HistorialEstado.cita_id == cita_id)
		.order_by(HistorialEstado.creado_en)
	)
	return list(db.scalars(stmt).all())


def create_recordatorio(db: Session, cita_id: UUID, programado_para: datetime) -> Recordatorio:
	"""Crea un recordatorio para una cita."""
	if not get_cita_by_id(db, cita_id):
		raise ValueError(f"No existe cita con id {cita_id}")

	nuevo_recordatorio = Recordatorio(cita_id=cita_id, programado_para=programado_para)
	db.add(nuevo_recordatorio)

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo crear el recordatorio") from exc

	db.refresh(nuevo_recordatorio)
	return nuevo_recordatorio


def get_recordatorios_pendientes(
	db: Session,
	antes_de: datetime | None = None,
) -> list[Recordatorio]:
	"""Lista recordatorios pendientes de envio hasta una fecha/hora limite."""
	fecha_limite = antes_de or utc_now()
	stmt = (
		select(Recordatorio)
		.where(
			Recordatorio.enviado.is_(False),
			Recordatorio.programado_para <= fecha_limite,
		)
		.order_by(Recordatorio.programado_para)
	)
	return list(db.scalars(stmt).all())


def get_metricas_citas(db: Session, dias: int = 7) -> dict:
	"""Obtiene metricas agregadas de citas para dashboard administrativo."""
	hoy = date.today()
	inicio_rango = hoy - timedelta(days=dias - 1)

	stmt_todas = select(Cita).where(
		Cita.fecha_cita >= inicio_rango,
		Cita.fecha_cita <= hoy,
	)
	citas_periodo = list(db.scalars(stmt_todas).all())

	total_periodo = len(citas_periodo)
	canceladas = sum(1 for c in citas_periodo if c.estado == "cancelada")
	tasa_cancelacion = round((canceladas / total_periodo * 100) if total_periodo > 0 else 0, 1)

	citas_hoy = [c for c in citas_periodo if c.fecha_cita == hoy]

	por_dia = {}
	for i in range(dias):
		d = inicio_rango + timedelta(days=i)
		por_dia[str(d)] = 0
	for c in citas_periodo:
		key = str(c.fecha_cita)
		if key in por_dia:
			por_dia[key] += 1

	por_dia_list = [
		{"fecha": fecha, "total": total}
		for fecha, total in sorted(por_dia.items())
	]

	por_especialidad = {}
	for c in citas_periodo:
		esp = c.especialidad_nombre or "Sin especialidad"
		por_especialidad[esp] = por_especialidad.get(esp, 0) + 1
	top_especialidades = sorted(
		[{"nombre": nombre, "total": total} for nombre, total in por_especialidad.items()],
		key=lambda x: x["total"],
		reverse=True,
	)[:5]

	por_medico = {}
	for c in citas_periodo:
		if c.medico_id:
			med_id = str(c.medico_id)
			if med_id not in por_medico:
				por_medico[med_id] = {"medico_id": med_id, "nombres": c.medico_nombre or "Sin nombre", "total": 0}
			por_medico[med_id]["total"] += 1
	top_medicos = sorted(por_medico.values(), key=lambda x: x["total"], reverse=True)[:5]

	return {
		"total_hoy": len(citas_hoy),
		"total_semana": total_periodo,
		"tasa_cancelacion": tasa_cancelacion,
		"canceladas": canceladas,
		"por_dia": por_dia_list,
		"top_especialidades": top_especialidades,
		"top_medicos": top_medicos,
	}


def marcar_recordatorio_enviado(db: Session, recordatorio_id: UUID) -> Recordatorio:
	"""Marca un recordatorio como enviado."""
	stmt = select(Recordatorio).where(Recordatorio.recordatorio_id == recordatorio_id)
	recordatorio = db.scalar(stmt)
	if not recordatorio:
		raise ValueError(f"No existe recordatorio con id {recordatorio_id}")

	recordatorio.enviado = True

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo marcar el recordatorio como enviado") from exc

	db.refresh(recordatorio)
	return recordatorio
