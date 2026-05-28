"""Modelos de base de datos para Notifications Service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Text, TIMESTAMP, event, text
from sqlalchemy import UUID as SAUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
	return datetime.now(timezone.utc)


class Notificacion(Base):
	__tablename__ = "notificaciones"

	notif_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		primary_key=True,
		nullable=False,
		server_default=text("gen_random_uuid()"),
	)
	medico_id: Mapped[uuid.UUID] = mapped_column(
		SAUUID(as_uuid=True),
		nullable=False,
	)
	tipo: Mapped[str] = mapped_column(String(50), nullable=False)
	titulo: Mapped[str] = mapped_column(String(255), nullable=False)
	descripcion: Mapped[str] = mapped_column(Text, nullable=False)
	leida: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=False,
		server_default=text("false"),
	)
	enlace: Mapped[str | None] = mapped_column(String(500), nullable=True)
	creado_en: Mapped[datetime] = mapped_column(
		TIMESTAMP,
		nullable=False,
		default=utc_now,
	)


@event.listens_for(Notificacion, "before_insert")
def set_sqlite_uuid_defaults(mapper, connection, target):
	if connection.dialect.name != "postgresql" and not target.notif_id:
		target.notif_id = uuid.uuid4()
