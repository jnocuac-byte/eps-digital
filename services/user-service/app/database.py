from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv
import os


# Carga variables de entorno desde .env para desarrollo local.
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Validacion temprana para evitar iniciar el servicio sin configuracion de DB.
if not DATABASE_URL:
	raise ValueError("DATABASE_URL no esta configurada en el archivo .env")

# Motor de SQLAlchemy para PostgreSQL (sin configuraciones especiales de SQLite).
engine = create_engine(DATABASE_URL)

# Fabrica de sesiones para operaciones transaccionales.
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
