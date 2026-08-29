from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Cita, HistorialEstado, Recordatorio
from app.schemas import CitaCreate, CitaUpdate

CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", "http://localhost:8004")
NOTIFICATIONS_SERVICE_URL = os.getenv("NOTIFICATIONS_SERVICE_URL", "http://localhost:8006")

TIPO_SERVICIO_A_SERVICIO = {
	"medicina_general": "Medicina General",
	"especialista": "Medicina Especializada",
	"urgencias": "Urgencias",
	"laboratorio": "Laboratorio",
}

# Zona horaria oficial de operacion (las reglas de anticipacion se calculan aqui).
ZONA_BOGOTA = ZoneInfo("America/Bogota")
# Anticipacion minima exigida para citas el mismo dia.
ANTELACION_MINIMA_MINUTOS = 60
# Duracion por defecto cuando la especialidad no informa duracion_cita_minutos.
DURACION_FALLBACK_MINUTOS = 20


def _obtener_medico_automatico(
	db: Session,
	tipo_servicio: str,
	especialidad_id: UUID | None,
	fecha_cita: date,
	hora_inicio: time,
	hora_fin: time,
) -> UUID | None:
	"""Obtiene un medico disponible automaticamente.

	Itera los medicos que cubren el horario segun catalog-service y devuelve
	el primero sin citas ya reservadas en eps_citas (evita 400 por cruce).
	"""
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
			for item in medicos:
				try:
					candidato = UUID(item["medico_id"])
				except (KeyError, TypeError, ValueError):
					continue
				if not es_horario_ocupado(
					db=db,
					medico_id=candidato,
					fecha=fecha_cita,
					hora_inicio=hora_inicio,
					hora_fin=hora_fin,
				):
					return candidato
	except Exception:
		return None
	return None


def utc_now() -> datetime:
	"""Retorna fecha/hora actual en UTC con timezone-aware."""
	return datetime.now(timezone.utc)


def hoy_bogota() -> date:
	"""Fecha actual en la zona horaria de operacion (America/Bogota)."""
	return datetime.now(ZONA_BOGOTA).date()


def ahora_bogota() -> datetime:
	"""Fecha/hora actual en la zona horaria de operacion (America/Bogota)."""
	return datetime.now(ZONA_BOGOTA)


def _validar_fecha_futura(fecha_cita: date, hora_inicio: time) -> None:
	"""Rechaza fechas pasadas y horas sin la anticipacion minima para el mismo dia."""
	hoy = hoy_bogota()
	if fecha_cita < hoy:
		raise ValueError("No se pueden agendar citas en fechas pasadas")
	if fecha_cita == hoy:
		limite = (ahora_bogota() + timedelta(minutes=ANTELACION_MINIMA_MINUTOS)).time()
		if hora_inicio < limite:
			raise ValueError(
				"Las citas para el dia de hoy requieren al menos "
				f"{ANTELACION_MINIMA_MINUTOS} minutos de anticipacion"
			)


def _obtener_duracion_especialidad(especialidad_id: UUID | None) -> int:
	"""Consulta duracion_cita_minutos en catalog-service con fallback configurable."""
	if especialidad_id is None:
		return DURACION_FALLBACK_MINUTOS
	try:
		with httpx.Client(timeout=10.0) as client:
			resp = client.get(f"{CATALOG_SERVICE_URL}/especialidades/{especialidad_id}")
		if resp.status_code != 200:
			return DURACION_FALLBACK_MINUTOS
		duracion = int(resp.json().get("duracion_cita_minutos") or DURACION_FALLBACK_MINUTOS)
	except Exception:
		return DURACION_FALLBACK_MINUTOS
	return max(1, min(duracion, 240))


def _obtener_disponibilidades_medico(medico_id: UUID, dia_semana: int) -> list[dict]:
	"""Trae los turnos activos de un medico para un dia de semana ISO (1-7)."""
	try:
		with httpx.Client(timeout=10.0) as client:
			resp = client.get(
				f"{CATALOG_SERVICE_URL}/disponibilidades/medico/{medico_id}",
				params={"dia_semana": dia_semana},
			)
		if resp.status_code != 200:
			return []
		data = resp.json()
	except Exception:
		return []
	return [t for t in data if isinstance(t, dict) and t.get("activo", False)]


def _iterar_slots(
	turno_inicio: time,
	turno_fin: time,
	duracion_minutos: int,
	fecha: date,
) -> list[tuple[time, time]]:
	"""Genera franjas consecutivas de duracion_minutos dentro de un turno."""
	base = datetime.combine(fecha, turno_inicio)
	fin_dt = datetime.combine(fecha, turno_fin)
	slots: list[tuple[time, time]] = []
	cursor = base
	while cursor + timedelta(minutes=duracion_minutos) <= fin_dt:
		slots.append((cursor.time(), (cursor + timedelta(minutes=duracion_minutos)).time()))
		cursor += timedelta(minutes=duracion_minutos)
	return slots


def _resolver_medicos_candidatos(
	fecha: date,
	medico_id: UUID | None = None,
	servicio_id: UUID | None = None,
	especialidad_id: UUID | None = None,
) -> list[UUID]:
	"""Resuelve medicos candidatos: el elegido o los auto-asignables para la fecha."""
	if medico_id is not None:
		return [medico_id]
	try:
		params: dict[str, str] = {"fecha": str(fecha)}
		if servicio_id is not None:
			params["servicio_id"] = str(servicio_id)
		if especialidad_id is not None:
			params["especialidad_id"] = str(especialidad_id)
		with httpx.Client(timeout=10.0) as client:
			resp = client.get(
				f"{CATALOG_SERVICE_URL}/medicos/disponibles",
				params=params,
			)
		if resp.status_code != 200:
			return []
		candidatos: list[UUID] = []
		for item in resp.json():
			try:
				candidatos.append(UUID(item["medico_id"]))
			except (KeyError, TypeError, ValueError):
				continue
		return candidatos
	except Exception:
		return []


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


def _crear_notificacion_medico(
	medico_id: UUID,
	tipo: str,
	titulo: str,
	descripcion: str,
) -> None:
	"""Inserta una notificacion interna en notifications-service (HTTP POST)."""
	try:
		with httpx.Client(timeout=5.0) as client:
			client.post(
				f"{NOTIFICATIONS_SERVICE_URL}/notificaciones",
				json={
					"medico_id": str(medico_id),
					"tipo": tipo,
					"titulo": titulo,
					"descripcion": descripcion,
				},
			)
	except Exception:
		pass


def create_cita(db: Session, cita_data: CitaCreate) -> Cita:
	"""Crea una cita validando fecha futura y disponibilidad horaria del medico."""
	_validar_fecha_futura(cita_data.fecha_cita, cita_data.hora_inicio)

	medico_id = cita_data.medico_id

	if medico_id is None:
		medico_id = _obtener_medico_automatico(
			db=db,
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

	_crear_notificacion_medico(
		medico_id=nueva_cita.medico_id,
		tipo="cita_nueva",
		titulo="Nueva cita agendada",
		descripcion=f"Cita programada para el {nueva_cita.fecha_cita} a las {nueva_cita.hora_inicio}",
	)

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


def cambiar_estado_cita(
	db: Session,
	cita_id: UUID,
	nuevo_estado: str,
	motivo: str | None,
	realizado_por: UUID,
) -> Cita:
	"""Cambia el estado de una cita programada y registra el historial."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	if nuevo_estado == cita.estado:
		return cita

	if cita.estado != "programada":
		raise ValueError(
			"Solo se puede cambiar el estado de una cita en estado 'programada'"
		)

	estado_anterior = cita.estado
	cita.estado = nuevo_estado

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo cambiar el estado de la cita") from exc

	add_historial_estado(
		db=db,
		cita_id=cita.cita_id,
		estado_anterior=estado_anterior,
		estado_nuevo=nuevo_estado,
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
	motivo: str | None = None,
) -> Cita:
	"""Reprograma una cita programada validando disponibilidad y registrando historial."""
	cita = get_cita_by_id(db, cita_id)
	if not cita:
		raise ValueError(f"No existe cita con id {cita_id}")

	if cita.estado != "programada":
		raise ValueError("Solo se puede reprogramar una cita en estado 'programada'")

	_validar_fecha_futura(nueva_fecha, nueva_hora_inicio)

	if es_horario_ocupado(
		db=db,
		medico_id=cita.medico_id,
		fecha=nueva_fecha,
		hora_inicio=nueva_hora_inicio,
		hora_fin=nueva_hora_fin,
		excluir_cita_id=cita.cita_id,
	):
		raise ValueError("El medico ya tiene una cita programada en el nuevo horario")

	cita.fecha_cita = nueva_fecha
	cita.hora_inicio = nueva_hora_inicio
	cita.hora_fin = nueva_hora_fin

	try:
		db.commit()
	except IntegrityError as exc:
		db.rollback()
		raise ValueError("No se pudo reprogramar la cita") from exc

	add_historial_estado(
		db=db,
		cita_id=cita.cita_id,
		estado_anterior="programada",
		estado_nuevo="programada",
		motivo=motivo or "Reprogramacion de cita",
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


def get_metricas_medico(db: Session, medico_id: UUID) -> dict:
	"""Obtiene metricas del dashboard para un medico especifico."""
	hoy = date.today()
	inicio_mes = hoy.replace(day=1)
	en_7_dias = hoy + timedelta(days=7)

	# Citas del medico en el mes actual
	stmt_mes = select(Cita).where(
		Cita.medico_id == medico_id,
		Cita.fecha_cita >= inicio_mes,
		Cita.fecha_cita <= hoy,
	)
	citas_mes = list(db.scalars(stmt_mes).all())

	# Citas de hoy
	citas_hoy = [c for c in citas_mes if c.fecha_cita == hoy and c.estado == "programada"]

	# Proximas 7 dias
	proximas_7 = [c for c in citas_mes if hoy < c.fecha_cita <= en_7_dias and c.estado == "programada"]

	# Atendidas este mes
	atendidas_mes = [c for c in citas_mes if c.estado == "atendida"]

	# Tasa de asistencia
	programadas_mes = [c for c in citas_mes if c.estado in ("programada", "atendida", "no_asistio")]
	asistidas = sum(1 for c in programadas_mes if c.estado == "atendida")
	tasa_asistencia = round((asistidas / len(programadas_mes) * 100) if programadas_mes else 0, 1)

	return {
		"citas_hoy": len(citas_hoy),
		"proximas_7_dias": len(proximas_7),
		"atendidas_mes": len(atendidas_mes),
		"tiempo_espera_promedio_min": 0,
		"tasa_asistencia_pct": tasa_asistencia,
		"ingresos_mes": 0,
	}


def generar_slots_disponibles(
	db: Session,
	fecha: date,
	medico_id: UUID | None = None,
	servicio_id: UUID | None = None,
	especialidad_id: UUID | None = None,
) -> list[dict[str, str]]:
	"""Calcula las franjas horarias disponibles para agendar una cita.

	Slots disponibles = turnos del medico (catalog-service)
	                    - citas programadas que se solapen (eps_citas)
	                    - franjas sin anticipacion minima si la fecha es hoy
	                      (America/Bogota). Fechas pasadas retornan [].
	"""
	if fecha < hoy_bogota():
		return []

	if medico_id is None and servicio_id is None and especialidad_id is None:
		raise ValueError("Se requiere medico_id, servicio_id o especialidad_id para consultar disponibilidad")

	duracion = _obtener_duracion_especialidad(especialidad_id)
	candidatos = _resolver_medicos_candidatos(fecha, medico_id, servicio_id, especialidad_id)
	if not candidatos:
		return []

	dia_semana = fecha.isoweekday()

	stmt = select(Cita).where(
		Cita.medico_id.in_(candidatos),
		Cita.fecha_cita == fecha,
		Cita.estado == "programada",
	)
	ocupadas: dict[UUID, list[Cita]] = {}
	for cita in db.scalars(stmt).all():
		ocupadas.setdefault(cita.medico_id, []).append(cita)

	def _solapa(inicio: time, fin: time, cita: Cita) -> bool:
		return cita.hora_inicio < fin and cita.hora_fin > inicio

	limite_hoy: time | None = None
	if fecha == hoy_bogota():
		limite_hoy = (ahora_bogota() + timedelta(minutes=ANTELACION_MINIMA_MINUTOS)).time()

	slots_por_hora: dict[time, time] = {}

	for medico in candidatos:
		citas_medico = ocupadas.get(medico, [])
		for turno in _obtener_disponibilidades_medico(medico, dia_semana):
			try:
				turno_inicio = time.fromisoformat(str(turno.get("hora_inicio"))[:8])
				turno_fin = time.fromisoformat(str(turno.get("hora_fin"))[:8])
			except ValueError:
				continue
			if turno_fin <= turno_inicio:
				continue
			for slot_inicio, slot_fin in _iterar_slots(turno_inicio, turno_fin, duracion, fecha):
				if any(_solapa(slot_inicio, slot_fin, c) for c in citas_medico):
					continue
				if limite_hoy is not None and slot_inicio < limite_hoy:
					continue
				slots_por_hora.setdefault(slot_inicio, slot_fin)

	return [
		{
			"hora_inicio": inicio.strftime("%H:%M"),
			"hora_fin": slots_por_hora[inicio].strftime("%H:%M"),
		}
		for inicio in sorted(slots_por_hora)
	]
