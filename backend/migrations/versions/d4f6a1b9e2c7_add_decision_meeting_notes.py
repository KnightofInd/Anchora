"""add_decision_meeting_notes

Revision ID: d4f6a1b9e2c7
Revises: c31f2d8e9a11
Create Date: 2026-03-29 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d4f6a1b9e2c7"
down_revision: Union[str, None] = "c31f2d8e9a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_meeting_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("decision_id", sa.UUID(), nullable=False),
        sa.Column("meeting_title", sa.String(length=255), nullable=True),
        sa.Column("transcript_text", sa.Text(), nullable=False),
        sa.Column("execution_guidance", sa.Text(), nullable=True),
        sa.Column("action_items", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decision_id"], ["decisions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_meeting_notes_decision_id", "decision_meeting_notes", ["decision_id"], unique=False)
    op.create_index("ix_decision_meeting_notes_created_at", "decision_meeting_notes", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_decision_meeting_notes_created_at", table_name="decision_meeting_notes")
    op.drop_index("ix_decision_meeting_notes_decision_id", table_name="decision_meeting_notes")
    op.drop_table("decision_meeting_notes")
