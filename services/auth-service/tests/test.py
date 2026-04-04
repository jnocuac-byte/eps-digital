import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import Base, SessionLocal, engine
from app.auth import registrar_usuario, autenticar_usuario, generar_tokens_para_credencial
from app.schemas import UserRegister
from datetime import date

# Asegura la creacion de tablas en ejecuciones locales de debug.
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 1. Registrar usuario
registro = UserRegister(
    nombres="Juan",
    apellidos="Perez",
    tipo_documento="CC",
    numero_documento="12345678",
    fecha_nacimiento=date(1990, 1, 1),
    correo=f"juan+{uuid.uuid4().hex[:8]}@test.com",
    telefono="3001234567",
    password="ClaveSegura1",
    confirm_password="ClaveSegura1",
    acepta_terminos=True
)

credencial = registrar_usuario(db, registro, ip="127.0.0.1", user_agent="test")
print(f"✅ Usuario registrado: {credencial.credencial_id}")

# 2. Autenticar
credencial_id, tiene_2fa = autenticar_usuario(db, registro.correo, "ClaveSegura1")
print(f"✅ Autenticado: {credencial_id}, 2FA: {tiene_2fa}")

# 3. Generar tokens
access, refresh = generar_tokens_para_credencial(credencial_id)
print(f"✅ Access token: {access[:50]}...")
print(f"✅ Refresh token: {refresh[:50]}...")

db.close()