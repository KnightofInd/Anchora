import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID]  = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]      = mapped_column(String(256), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True, nullable=False)

    # JSON logic rule — evaluated by the policy engine
    # Example: {"condition": "risk_score > 7", "action": "require_senior_approval"}
    rule_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    compliance_checks: Mapped[list["ComplianceCheck"]] = relationship(
        "ComplianceCheck", back_populates="policy"
    )

    def __repr__(self) -> str:
        return f"<Policy {self.name}>"
