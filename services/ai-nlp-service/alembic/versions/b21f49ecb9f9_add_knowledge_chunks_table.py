"""add_knowledge_chunks_table

Revision ID: b21f49ecb9f9
Revises: b2c4d6e8f0a2
Create Date: 2026-09-27 18:07:15.218707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'b21f49ecb9f9'
down_revision: Union[str, Sequence[str], None] = 'b2c4d6e8f0a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Solo crea knowledge_chunks: el autogenerate also detecto como "removidas"
    las tablas de los demas servicios (comparten esquema public) y esas se
    excluyeron a proposito.
    """
    op.create_table(
        'knowledge_chunks',
        sa.Column('chunk_id', sa.UUID(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=True),
        sa.Column('contenido', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(768), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('chunk_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('knowledge_chunks')
