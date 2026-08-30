"""add estado_orquestador to conversacion

Revision ID: b2c4d6e8f0a2
Revises: aebd3ba94d80
Create Date: 2026-08-30 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c4d6e8f0a2'
down_revision: Union[str, Sequence[str], None] = 'aebd3ba94d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add estado_orquestador column to conversacion table."""
    op.add_column(
        'conversacion',
        sa.Column('estado_orquestador', sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove estado_orquestador column from conversacion table."""
    op.drop_column('conversacion', 'estado_orquestador')
