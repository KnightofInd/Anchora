from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.workflow import Workflow
    from app.models.compliance import ComplianceCheck


class DecisionStatus(str, Enum):
    DRAFT    = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class Decision(Base):
    """
    The central first-class object in Anchora.
    Every field here is mandatory for full traceability.
    """
    __tablename__ = "decisions"

    id: Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str]            = mapped_column(String(512), nullable=False)
    description: Mapped[str]      = mapped_column(Text, nullable=True)

    # AI-generated fields (must store AI metadata for reproducibility)
    reasoning_summary: Mapped[str]   = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float]  = mapped_column(Float, nullable=True)
    risk_score: Mapped[float]        = mapped_column(Float, nullable=True)
    assumptions: Mapped[dict]        = mapped_column(JSONB, default=list, nullable=False)

    # AI metadata (academic integrity / reproducibility)
    ai_model_name: Mapped[str]      = mapped_column(String(128), nullable=True)
    ai_model_version: Mapped[str]   = mapped_column(String(64), nullable=True)
    ai_prompt_version: Mapped[str]  = mapped_column(String(64), nullable=True)

    # Status lifecycle — enforced as strict enum
    status: Mapped[str] = mapped_column(
        String(32), default=DecisionStatus.DRAFT, nullable=False
    )

    # Traceability: creator
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    creator: Mapped["User"] = relationship("User", back_populates="decisions")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    references: Mapped[list["DecisionReference"]] = relationship(
        "DecisionReference", back_populates="decision", cascade="all, delete-orphan"
    )
    workflows:  Mapped[list["Workflow"]]   = relationship("Workflow",         back_populates="decision")
    compliance: Mapped[list["ComplianceCheck"]] = relationship("ComplianceCheck", back_populates="decision")

    def __repr__(self) -> str:
        return f"<Decision {self.title} [{self.status}]>"


class DecisionReference(Base):
    """
    Links a Decision to its source documents and data inputs.
    This is what enables end-to-end traceability.
    """
    __tablename__ = "decision_references"

    id: Mapped[uuid.UUID]         = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True
    )
    data_source: Mapped[str]      = mapped_column(String(512), nullable=True)
    reference_type: Mapped[str]   = mapped_column(String(64), nullable=False)  # e.g. "document", "api", "manual"

    decision: Mapped["Decision"]  = relationship("Decision", back_populates="references")
    document: Mapped["Document"]  = relationship("Document", back_populates="decision_references")

    def __repr__(self) -> str:
        return f"<DecisionReference decision={self.decision_id} doc={self.document_id}>"
