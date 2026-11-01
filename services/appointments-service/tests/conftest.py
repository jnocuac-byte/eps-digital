"""Infraestructura pytest minima para appointments-service (PR4b).

Usa una base SQLite en archivo temporal, asi los tests corren sin PostgreSQL
ni servicios externos. DATABASE_URL se fija ANTES de importar app.database,
porque el engine se crea en tiempo de importacion.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_tmpdir = tempfile.mkdtemp(prefix="eps_citas_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmpdir) / 'citas_test.db'}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def db():
    """Sesion SQLAlchemy aislada por test (esquema recreado en cada test)."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    """TestClient de FastAPI con get_db sobrescrito por la sesion de prueba."""

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    # Sin context manager: no se ejecuta lifespan (que llama setup_logger() y
    # depende de LOG_LEVEL del entorno); el esquema lo crea el fixture db.
    yield TestClient(app)
    app.dependency_overrides.clear()
