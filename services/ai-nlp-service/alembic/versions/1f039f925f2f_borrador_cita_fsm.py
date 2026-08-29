"""borrador_cita fsm

Revision ID: 1f039f925f2f
Revises: aebd3ba94d80
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1f039f925f2f'
down_revision: Union[str, Sequence[str], None] = 'aebd3ba94d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('borrador_cita',
    sa.Column('borrador_id', sa.UUID(), nullable=False),
    sa.Column('conversacion_id', sa.UUID(), nullable=False),
    sa.Column('estado', sa.String(length=30), nullable=False),
    sa.Column('especialidad_id', sa.String(length=64), nullable=True),
    sa.Column('especialidad_nombre', sa.String(length=120), nullable=True),
    sa.Column('medico_id', sa.String(length=64), nullable=True),
    sa.Column('medico_nombre', sa.String(length=120), nullable=True),
    sa.Column('sede_id', sa.String(length=64), nullable=True),
    sa.Column('sede_nombre', sa.String(length=120), nullable=True),
    sa.Column('fecha', sa.String(length=10), nullable=True),
    sa.Column('hora', sa.String(length=5), nullable=True),
    sa.Column('opciones_mostradas', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversacion_id'], ['conversacion.conversacion_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('borrador_id'),
    sa.UniqueConstraint('conversacion_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('borrador_cita')
