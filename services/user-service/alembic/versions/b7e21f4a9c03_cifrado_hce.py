"""cifrado HCE: columnas cifradas + indices ciegos

Revision ID: b7e21f4a9c03
Revises: dabf49b70012
Create Date: 2026-10-18 12:00:00.000000

Cifra en columna los datos sensibles de historia clinica
(``informacion_medica``) y de identidad (``usuarios.numero_documento`` y
``usuarios.correo``), y agrega indices ciegos (HMAC-SHA256) para conservar las
busquedas por igualdad y las restricciones UNIQUE.

Pasos:
    1. Ampliar a TEXT las columnas que almacenaran el token Fernet.
    2. Eliminar las restricciones UNIQUE de las columnas cifradas (el texto
       cifrado con Fernet no es determinista).
    3. Agregar las columnas de indice ciego (nullable, para permitir el backfill).
    4. Backfill: cifrar los datos existentes y calcular los indices ciegos.
    5. Exigir NOT NULL y crear UNIQUE sobre los indices ciegos.

Requiere ``HCE_ENCRYPTION_KEYS`` y ``HCE_BLIND_INDEX_KEY`` (ver
``app/core/crypto.py``). Si no hay filas que cifrar, el backfill no las usa.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.crypto import blind_index, decrypt_value, encrypt_value, is_encrypted

# revision identifiers, used by Alembic.
revision: str = "b7e21f4a9c03"
down_revision: Union[str, Sequence[str], None] = "dabf49b70012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

HASH_LEN = 64


def _a_texto(value):
    """Cifra el valor si aun no esta cifrado (idempotente)."""
    if value is None:
        return None
    return value if is_encrypted(value) else encrypt_value(value)


def _a_plano(value):
    """Devuelve el texto plano de un valor, este cifrado o no."""
    if value is None:
        return None
    return decrypt_value(value) if is_encrypted(value) else value


def _drop_unique_constraints(bind, table: str, column: str) -> None:
    """Elimina las restricciones UNIQUE que cubran exactamente la columna dada."""
    filas = bind.execute(
        sa.text(
            """
            SELECT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_name = :table
              AND tc.constraint_type = 'UNIQUE'
              AND kcu.column_name = :column
              AND tc.table_schema NOT IN ('pg_catalog', 'information_schema')
            """
        ),
        {"table": table, "column": column},
    ).fetchall()
    for (nombre,) in filas:
        op.drop_constraint(nombre, table, type_="unique")


def _backfill_usuarios(bind) -> None:
    """Cifra numero_documento/correo y calcula sus indices ciegos."""
    filas = bind.execute(
        sa.text("SELECT usuario_id, numero_documento, correo FROM usuarios")
    ).mappings().all()
    for fila in filas:
        doc_plano = _a_plano(fila["numero_documento"])
        correo_plano = _a_plano(fila["correo"])
        bind.execute(
            sa.text(
                "UPDATE usuarios SET numero_documento = :doc, correo = :correo, "
                "numero_documento_hash = :doc_hash, correo_hash = :correo_hash "
                "WHERE usuario_id = :uid"
            ),
            {
                # Se conserva el valor almacenado (idempotente); solo el hash
                # necesita el texto plano.
                "doc": _a_texto(fila["numero_documento"]),
                "correo": _a_texto(fila["correo"]),
                "doc_hash": blind_index(doc_plano),
                "correo_hash": blind_index(correo_plano, casefold=True),
                "uid": fila["usuario_id"],
            },
        )


def _backfill_informacion_medica(bind) -> None:
    """Cifra los campos sensibles de la historia clinica electronica."""
    filas = bind.execute(
        sa.text(
            "SELECT info_medica_id, tipo_sangre, alergias, enfermedades_cronicas, "
            "medicamentos_actuales FROM informacion_medica"
        )
    ).mappings().all()
    for fila in filas:
        bind.execute(
            sa.text(
                "UPDATE informacion_medica SET tipo_sangre = :ts, alergias = :al, "
                "enfermedades_cronicas = :ec, medicamentos_actuales = :ma "
                "WHERE info_medica_id = :iid"
            ),
            {
                "ts": _a_texto(fila["tipo_sangre"]),
                "al": _a_texto(fila["alergias"]),
                "ec": _a_texto(fila["enfermedades_cronicas"]),
                "ma": _a_texto(fila["medicamentos_actuales"]),
                "iid": fila["info_medica_id"],
            },
        )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1) Ampliar a TEXT las columnas que almacenaran el token Fernet.
    op.alter_column(
        "usuarios", "numero_documento",
        existing_type=sa.String(length=20), type_=sa.Text(), existing_nullable=False,
    )
    op.alter_column(
        "usuarios", "correo",
        existing_type=sa.String(length=255), type_=sa.Text(), existing_nullable=False,
    )
    op.alter_column(
        "informacion_medica", "tipo_sangre",
        existing_type=sa.String(length=5), type_=sa.Text(), existing_nullable=True,
    )

    # 2) Quitar UNIQUE de las columnas cifradas (indeterministas con Fernet).
    _drop_unique_constraints(bind, "usuarios", "numero_documento")
    _drop_unique_constraints(bind, "usuarios", "correo")

    # 3) Agregar columnas de indice ciego (nullable para el backfill).
    op.add_column(
        "usuarios",
        sa.Column("numero_documento_hash", sa.String(length=HASH_LEN), nullable=True),
    )
    op.add_column(
        "usuarios",
        sa.Column("correo_hash", sa.String(length=HASH_LEN), nullable=True),
    )

    # 4) Backfill: cifrar datos existentes y calcular indices ciegos.
    _backfill_usuarios(bind)
    _backfill_informacion_medica(bind)

    # 5) Exigir NOT NULL y proteger por UNIQUE los indices ciegos.
    op.alter_column(
        "usuarios", "numero_documento_hash",
        existing_type=sa.String(length=HASH_LEN), nullable=False,
    )
    op.alter_column(
        "usuarios", "correo_hash",
        existing_type=sa.String(length=HASH_LEN), nullable=False,
    )
    op.create_unique_constraint(
        "uq_usuarios_numero_documento_hash", "usuarios", ["numero_documento_hash"]
    )
    op.create_unique_constraint(
        "uq_usuarios_correo_hash", "usuarios", ["correo_hash"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # Descifrar datos antes de reducir las columnas y restaurar la unicidad.
    filas_usuarios = bind.execute(
        sa.text("SELECT usuario_id, numero_documento, correo FROM usuarios")
    ).mappings().all()
    for fila in filas_usuarios:
        bind.execute(
            sa.text(
                "UPDATE usuarios SET numero_documento = :doc, correo = :correo "
                "WHERE usuario_id = :uid"
            ),
            {
                "doc": _a_plano(fila["numero_documento"]),
                "correo": _a_plano(fila["correo"]),
                "uid": fila["usuario_id"],
            },
        )

    filas_medicas = bind.execute(
        sa.text(
            "SELECT info_medica_id, tipo_sangre, alergias, enfermedades_cronicas, "
            "medicamentos_actuales FROM informacion_medica"
        )
    ).mappings().all()
    for fila in filas_medicas:
        bind.execute(
            sa.text(
                "UPDATE informacion_medica SET tipo_sangre = :ts, alergias = :al, "
                "enfermedades_cronicas = :ec, medicamentos_actuales = :ma "
                "WHERE info_medica_id = :iid"
            ),
            {
                "ts": _a_plano(fila["tipo_sangre"]),
                "al": _a_plano(fila["alergias"]),
                "ec": _a_plano(fila["enfermedades_cronicas"]),
                "ma": _a_plano(fila["medicamentos_actuales"]),
                "iid": fila["info_medica_id"],
            },
        )

    # Quitar indices ciegos.
    op.drop_constraint("uq_usuarios_numero_documento_hash", "usuarios", type_="unique")
    op.drop_constraint("uq_usuarios_correo_hash", "usuarios", type_="unique")
    op.drop_column("usuarios", "correo_hash")
    op.drop_column("usuarios", "numero_documento_hash")

    # Restaurar UNIQUE y tipos originales.
    op.create_unique_constraint("usuarios_numero_documento_key", "usuarios", ["numero_documento"])
    op.create_unique_constraint("usuarios_correo_key", "usuarios", ["correo"])
    op.alter_column(
        "usuarios", "numero_documento",
        existing_type=sa.Text(), type_=sa.String(length=20), existing_nullable=False,
    )
    op.alter_column(
        "usuarios", "correo",
        existing_type=sa.Text(), type_=sa.String(length=255), existing_nullable=False,
    )
    op.alter_column(
        "informacion_medica", "tipo_sangre",
        existing_type=sa.Text(), type_=sa.String(length=5), existing_nullable=True,
    )
