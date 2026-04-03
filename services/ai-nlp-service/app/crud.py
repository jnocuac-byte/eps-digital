from __future__ import annotations

from datetime import timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ClasificacionSintomas, Conversacion, Mensaje, utc_now


# CONVERSACION
def crear_conversacion(db: Session, usuario_id: UUID) -> Conversacion:
	"""Crea una nueva conversacion en estado activa."""
	conversacion = Conversacion(usuario_id=usuario_id)
	db.add(conversacion)
	db.commit()
	db.refresh(conversacion)
	return conversacion


def get_conversacion(db: Session, conversacion_id: UUID) -> Conversacion | None:
	"""Obtiene una conversacion por su ID."""
	stmt = select(Conversacion).where(Conversacion.conversacion_id == conversacion_id)
	return db.scalar(stmt)


def get_conversaciones_by_usuario(
	db: Session,
	usuario_id: UUID,
	limit: int = 50,
) -> list[Conversacion]:
	"""Lista conversaciones de un usuario, mas recientes primero."""
	stmt = (
		select(Conversacion)
		.where(Conversacion.usuario_id == usuario_id)
		.order_by(Conversacion.iniciada_en.desc())
		.limit(limit)
	)
	return list(db.scalars(stmt).all())


def cerrar_conversacion(db: Session, conversacion_id: UUID) -> Conversacion:
	"""Marca una conversacion como cerrada y registra fecha de cierre."""
	conversacion = get_conversacion(db, conversacion_id)
	if conversacion is None:
		raise ValueError("Conversacion no encontrada")

	conversacion.estado = "cerrada"
	conversacion.cerrada_en = utc_now().astimezone(timezone.utc)
	db.commit()
	db.refresh(conversacion)
	return conversacion


# MENSAJE
def crear_mensaje(
	db: Session,
	conversacion_id: UUID,
	remitente: str,
	contenido: str,
) -> Mensaje:
	"""Crea un mensaje asociado a una conversacion."""
	mensaje = Mensaje(
		conversacion_id=conversacion_id,
		remitente=remitente,
		contenido=contenido,
	)
	db.add(mensaje)
	db.commit()
	db.refresh(mensaje)
	return mensaje


def get_mensajes_by_conversacion(
	db: Session,
	conversacion_id: UUID,
	limit: int = 100,
) -> list[Mensaje]:
	"""Obtiene mensajes de una conversacion ordenados por fecha ascendente."""
	stmt = (
		select(Mensaje)
		.where(Mensaje.conversacion_id == conversacion_id)
		.order_by(Mensaje.creado_en.asc())
		.limit(limit)
	)
	return list(db.scalars(stmt).all())


# CLASIFICACION_SINTOMAS
def crear_clasificacion(db: Session, clasificacion_data: dict) -> ClasificacionSintomas:
	"""Crea una clasificacion de sintomas a partir de un diccionario de datos."""
	confianza_valor = clasificacion_data.get("confianza_modelo")
	confianza_decimal = None
	if confianza_valor is not None:
		confianza_decimal = Decimal(str(confianza_valor))

	clasificacion = ClasificacionSintomas(
		conversacion_id=clasificacion_data["conversacion_id"],
		terminos_identificados=clasificacion_data.get("terminos_identificados"),
		especialidad_sugerida=clasificacion_data.get("especialidad_sugerida"),
		nivel_urgencia=clasificacion_data["nivel_urgencia"],
		confianza_modelo=confianza_decimal,
	)
	db.add(clasificacion)
	db.commit()
	db.refresh(clasificacion)
	return clasificacion


def get_clasificacion_by_conversacion(
	db: Session,
	conversacion_id: UUID,
) -> ClasificacionSintomas | None:
	"""Obtiene la clasificacion asociada a una conversacion."""
	stmt = select(ClasificacionSintomas).where(
		ClasificacionSintomas.conversacion_id == conversacion_id
	)
	return db.scalar(stmt)