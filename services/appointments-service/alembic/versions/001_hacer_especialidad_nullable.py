"""Hacer especialidad_id nullable

Revision ID: 001
Revises:
Create Date: 2026-05-17

"""
from alembic import op

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('citas', 'especialidad_id', nullable=True)


def downgrade() -> None:
    op.alter_column('citas', 'especialidad_id', nullable=False)