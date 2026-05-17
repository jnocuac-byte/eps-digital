from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import Boolean, Date, ForeignKey, Index, String, Text, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utc_now() -> datetime:
	"""Retorna fecha/hora actual en UTC con timezone-aware."""
	return datetime.now(timezone.utc)


class Cita(Base):
	"""Entidad principal de cita medica."""

	__tablename__ = "citas"

	__table_args__ = (
		Index("ix_citas_usuario_id", "usuario_id"),
		Index("ix_citas_medico_id", "medico_id"),
		Index("ix_citas_fecha_cita", "fecha_cita"),
		Index("ix_citas_estado", "estado"),
	)

	# Identificador unico de la cita (PK).
	cita_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		default=uuid.uuid4,
	)

	# Referencia al usuario en User Service.
	usuario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

	# Referencia al medico en Catalogo Service.
	medico_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

	# Referencia a la especialidad en Catalogo Service.
	especialidad_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

	# Tipo de servicio: medicina_general, especialista, urgencias, laboratorio.
	tipo_servicio: Mapped[str] = mapped_column(String(50), nullable=False)

	# Fecha y franja horaria de la cita.
	fecha_cita: Mapped[date] = mapped_column(Date, nullable=False)
	hora_inicio: Mapped[time] = mapped_column(nullable=False)
	hora_fin: Mapped[time] = mapped_column(nullable=False)

	# Referencia a la sede en Catalogo Service.
	sede_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

	# Descripcion opcional de sintomas reportados por el usuario.
	descripcion_sintomas: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Estado actual de la cita: programada, cancelada, atendida, no_asistio.
	estado: Mapped[str] = mapped_column(String(20), nullable=False, default="programada")

	# Campos de auditoria de creacion y actualizacion.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)
	actualizado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
		onupdate=utc_now,
	)

	# Historial de cambios de estado asociados a la cita.
	historial_estados: Mapped[list[HistorialEstado]] = relationship(
		back_populates="cita",
		cascade="all, delete-orphan",
		passive_deletes=True,
	)

	# Recordatorios programados para la cita.
	recordatorios: Mapped[list[Recordatorio]] = relationship(
		back_populates="cita",
		cascade="all, delete-orphan",
		passive_deletes=True,
	)


class HistorialEstado(Base):
	"""Historial de transiciones de estado de una cita."""

	__tablename__ = "historial_estado"

	# Identificador unico del historial (PK).
	historial_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		default=uuid.uuid4,
	)

	# Relacion con cita, eliminando en cascada al borrar la cita padre.
	cita_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("citas.cita_id", ondelete="CASCADE"),
		nullable=False,
	)

	# Valores de estado antes y despues de la transicion.
	estado_anterior: Mapped[str] = mapped_column(String(20), nullable=False)
	estado_nuevo: Mapped[str] = mapped_column(String(20), nullable=False)

	# Motivo opcional del cambio de estado.
	motivo: Mapped[str | None] = mapped_column(Text, nullable=True)

	# Usuario que realizo el cambio de estado.
	realizado_por: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

	# Fecha/hora de creacion del registro historico.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)

	# Navegacion inversa hacia la cita.
	cita: Mapped[Cita] = relationship(back_populates="historial_estados")


class Recordatorio(Base):
	"""Recordatorios asociados a citas para notificaciones previas."""

	__tablename__ = "recordatorios"

	# Identificador unico del recordatorio (PK).
	recordatorio_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		default=uuid.uuid4,
	)

	# Relacion con cita, eliminando en cascada al borrar la cita padre.
	cita_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("citas.cita_id", ondelete="CASCADE"),
		nullable=False,
	)

	# Fecha/hora planificada para enviar el recordatorio (ej. 24h antes).
	programado_para: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)

	# Estado de envio del recordatorio.
	enviado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	# Fecha/hora de creacion del recordatorio.
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)

	# Navegacion inversa hacia la cita.
	cita: Mapped[Cita] = relationship(back_populates="recordatorios")
