from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.decision import Decision
    from app.models.policy import Policy


class ComplianceStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    decision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id", ondelete="RESTRICT"), nullable=False
    )
    decision: Mapped["Decision"] = relationship("Decision", back_populates="compliance")

    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("policies.id", ondelete="RESTRICT"), nullable=False
    )
    policy: Mapped["Policy"] = relationship("Policy", back_populates="compliance_checks")

    status: Mapped[str] = mapped_column(
        String(16), default=ComplianceStatus.PASS, nullable=False
    )

    violations: Mapped[dict]  = mapped_column(JSONB, default=list, nullable=False)
    risk_notes: Mapped[dict]  = mapped_column(JSONB, default=dict, nullable=False)

    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ComplianceCheck decision={self.decision_id} policy={self.policy_id} [{self.status}]>"
