from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.decision import Decision


class WorkflowStatus(str, Enum):
    PENDING     = "pending"
    IN_REVIEW   = "in_review"
    APPROVED    = "approved"
    REJECTED    = "rejected"
    EXECUTED    = "executed"


class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    OVERDUE     = "overdue"


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped["Decision"] = relationship("Decision", back_populates="workflows")

    status: Mapped[str] = mapped_column(
        String(32), default=WorkflowStatus.PENDING, nullable=False
    )

    triggered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Workflow decision={self.decision_id} [{self.status}]>"


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="tasks")

    assigned_to: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    title: Mapped[str]          = mapped_column(String(256), nullable=False)
    description: Mapped[str]    = mapped_column(Text, nullable=True)
    status: Mapped[str]         = mapped_column(String(32), default=TaskStatus.PENDING, nullable=False)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    approval_notes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<Task {self.title} [{self.status}]>"
