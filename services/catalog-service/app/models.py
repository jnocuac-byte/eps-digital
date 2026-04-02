from __future__ import annotations

from datetime import datetime, time, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
	Boolean,
	CheckConstraint,
	ForeignKey,
	Index,
	SmallInteger,
	String,
	Text,
	Time,
	TIMESTAMP,
	UniqueConstraint,
	Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.database import Base

def utc_now() -> datetime:
	"""Retorna la fecha y hora actual en UTC con zona horaria."""
	return datetime.now(timezone.utc)


class Servicio(Base):
	"""Agrupa las especialidades medicas por tipo de servicio."""

	__tablename__ = "servicios"
	__table_args__ = (Index("nombre_servicio", "nombre"),)

	servicio_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	nombre: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
	descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
	icono: Mapped[str | None] = mapped_column(String(100), nullable=True)
	activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP(timezone=True), nullable=False, default=utc_now
	)

	# Relacion 1:N con especialidades.
	especialidades: Mapped[list[Especialidad]] = relationship(
		back_populates="servicio", cascade="all, delete-orphan"
	)


class Especialidad(Base):
	"""Define una especialidad medica perteneciente a un servicio."""

	__tablename__ = "especialidades"
	__table_args__ = (Index("especialidad_nombre", "nombre"),)

	especialidad_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	servicio_id: Mapped[UUID] = mapped_column(
		Uuid, ForeignKey("servicios.servicio_id"), nullable=False
	)
	nombre: Mapped[str] = mapped_column(String(100), nullable=False)
	descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
	duracion_cita_minutos: Mapped[int] = mapped_column(
		SmallInteger, nullable=False, default=20
	)
	activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP(timezone=True), nullable=False, default=utc_now
	)

	servicio: Mapped[Servicio] = relationship(back_populates="especialidades")
	medico_especialidades: Mapped[list[MedicoEspecialidad]] = relationship(
		back_populates="especialidad", cascade="all, delete-orphan"
	)
	disponibilidades: Mapped[list[Disponibilidad]] = relationship(
		back_populates="especialidad", cascade="all, delete-orphan"
	)


class Medico(Base):
	"""Profesional de salud habilitado para atencion por especialidad."""

	__tablename__ = "medicos"
	__table_args__ = (Index("medico_registro", "numero_registro"),)

	medico_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	nombres: Mapped[str] = mapped_column(String(100), nullable=False)
	apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
	numero_registro: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
	correo_institucional: Mapped[str] = mapped_column(
		String(255), nullable=False, unique=True
	)
	activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP(timezone=True), nullable=False, default=utc_now
	)

	medico_especialidades: Mapped[list[MedicoEspecialidad]] = relationship(
		back_populates="medico", cascade="all, delete-orphan"
	)
	disponibilidades: Mapped[list[Disponibilidad]] = relationship(
		back_populates="medico", cascade="all, delete-orphan"
	)


class MedicoEspecialidad(Base):
	"""Tabla intermedia para la relacion N:M entre medico y especialidad."""

	__tablename__ = "medico_especialidades"
	__table_args__ = (
		UniqueConstraint(
			"medico_id",
			"especialidad_id",
			name="uq_medico_especialidad_medico_especialidad",
		),
	)

	medico_especialidad_id: Mapped[UUID] = mapped_column(
		Uuid, primary_key=True, default=uuid4
	)
	medico_id: Mapped[UUID] = mapped_column(
		Uuid, ForeignKey("medicos.medico_id"), nullable=False
	)
	especialidad_id: Mapped[UUID] = mapped_column(
		Uuid, ForeignKey("especialidades.especialidad_id"), nullable=False
	)
	es_principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

	medico: Mapped[Medico] = relationship(back_populates="medico_especialidades")
	especialidad: Mapped[Especialidad] = relationship(
		back_populates="medico_especialidades"
	)


class Sede(Base):
	"""Sede fisica donde se prestan los servicios de salud."""

	__tablename__ = "sedes"

	sede_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	nombre: Mapped[str] = mapped_column(String(100), nullable=False)
	direccion: Mapped[str] = mapped_column(String(200), nullable=False)
	ciudad: Mapped[str] = mapped_column(String(100), nullable=False)
	telefono: Mapped[str | None] = mapped_column(String(20), nullable=True)
	activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP(timezone=True), nullable=False, default=utc_now
	)

	disponibilidades: Mapped[list[Disponibilidad]] = relationship(
		back_populates="sede", cascade="all, delete-orphan"
	)


class Disponibilidad(Base):
	"""Define la franja semanal disponible para un medico en una sede."""

	__tablename__ = "disponibilidades"
	__table_args__ = (
		Index("disponibilidad_medico_fecha", "medico_id", "dia_semana", "hora_inicio"),
		CheckConstraint("dia_semana BETWEEN 1 AND 7", name="ck_disponibilidad_dia_semana"),
	)

	disponibilidad_id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
	medico_id: Mapped[UUID] = mapped_column(
		Uuid, ForeignKey("medicos.medico_id"), nullable=False
	)
	especialidad_id: Mapped[UUID] = mapped_column(
		Uuid, ForeignKey("especialidades.especialidad_id"), nullable=False
	)
	sede_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("sedes.sede_id"), nullable=False)
	dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
	hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
	hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
	activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP(timezone=True), nullable=False, default=utc_now
	)

	medico: Mapped[Medico] = relationship(back_populates="disponibilidades")
	especialidad: Mapped[Especialidad] = relationship(back_populates="disponibilidades")
	sede: Mapped[Sede] = relationship(back_populates="disponibilidades")
