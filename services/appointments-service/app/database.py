from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
	raise ValueError("DATABASE_URL no esta configurada en el archivo .env")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
	"""Clase base para todos los modelos ORM del servicio."""

def get_db():
	"""Provee una sesion de base de datos por request y asegura su cierre."""
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()
