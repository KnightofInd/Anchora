"""add_context_to_decisions

Revision ID: c31f2d8e9a11
Revises: b7b9d1a4c3f2
Create Date: 2026-03-25 18:15:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c31f2d8e9a11"
down_revision: Union[str, None] = "b7b9d1a4c3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decisions", sa.Column("context", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("decisions", "context")
