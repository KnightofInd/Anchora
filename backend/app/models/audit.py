import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, event, DDL, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AuditLog(Base):
    """
    IMMUTABLE audit log — append-only by design and by DB constraint.
    No UPDATE or DELETE is ever permitted on this table.

    Hash chaining can be added in a future phase for tamper resistance.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID]     = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str]  = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[str]    = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str]       = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    # Rich context: policy result, risk scores, AI metadata, etc.
    meta: Mapped[dict]    = mapped_column("metadata", JSONB, default=dict, nullable=False)

    def __repr__(self) -> str:
        return f"<AuditLog {self.entity_type}:{self.entity_id} {self.action} by {self.performed_by}>"


# ─── DB-level immutability rule ───────────────────────────────────────────────
# Postgres rule that silently blocks UPDATE and DELETE on audit_logs.
# Applied via Alembic migration using a DDL event.

_prevent_update = DDL(
    """
    CREATE OR REPLACE RULE audit_logs_no_update AS
        ON UPDATE TO audit_logs DO INSTEAD NOTHING;
    """
)

_prevent_delete = DDL(
    """
    CREATE OR REPLACE RULE audit_logs_no_delete AS
        ON DELETE TO audit_logs DO INSTEAD NOTHING;
    """
)

event.listen(
    AuditLog.__table__,
    "after_create",
    _prevent_update.execute_if(dialect="postgresql"),
)
event.listen(
    AuditLog.__table__,
    "after_create",
    _prevent_delete.execute_if(dialect="postgresql"),
)
