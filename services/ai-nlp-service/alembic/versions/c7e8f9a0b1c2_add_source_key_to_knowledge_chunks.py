"""add source_key to knowledge_chunks.

Revision ID: c7e8f9a0b1c2
Revises: b21f49ecb9f9
Create Date: 2026-10-24 12:20:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "b21f49ecb9f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "knowledge_chunks",
        sa.Column("source_key", sa.String(length=255), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE knowledge_chunks
            SET source_key = 'guide:' || tipo || ':' ||
                COALESCE(nombre, chunk_id::text)
            WHERE source_key IS NULL
            """
        )
    )
    op.alter_column("knowledge_chunks", "source_key", nullable=False)
    op.create_unique_constraint(
        "uq_knowledge_chunks_source_key",
        "knowledge_chunks",
        ["source_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_knowledge_chunks_source_key",
        "knowledge_chunks",
        type_="unique",
    )
    op.drop_column("knowledge_chunks", "source_key")
