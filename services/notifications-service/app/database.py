"""Configuracion de base de datos para Notifications Service."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql://eps_user:eps_password@localhost:5432/eps_notifications",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
	pass


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
