"""
Audit Engine
------------
The central, non-bypassable audit logging service.

Every module MUST call:
    await audit.log(db, entity_type, entity_id, action, performed_by, metadata)

The AUDIT_LOGS table has a DB-level constraint preventing UPDATE/DELETE.
This service enforces append-only writes.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditEngine:
    """
    Singleton-style audit service.
    Import and call from any module — never inline audit logic.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        *,
        entity_type: str,
        entity_id: str | UUID,
        action: str,
        performed_by: str | UUID,
        metadata: dict[str, Any] | None = None,
    ) -> AuditLog:
        """
        Creates an immutable audit record.

        Args:
            db:           Active DB session.
            entity_type:  e.g. "decision", "workflow", "document", "user"
            entity_id:    UUID of the entity being acted upon.
            action:       e.g. "created", "approved", "rejected", "uploaded"
            performed_by: UUID of the user performing the action.
            metadata:     Any additional context (policy result, risk score, etc.)

        Returns:
            The persisted AuditLog ORM object.
        """
        entry = AuditLog(
            entity_type=entity_type,
            entity_id=str(entity_id),
            action=action,
            performed_by=str(performed_by),
            timestamp=datetime.now(timezone.utc),
            meta=metadata or {},
        )

        db.add(entry)
        await db.flush()   # write within caller's transaction
        return entry


# ─── Module-level singleton for convenient import ────────────────────────────
audit = AuditEngine()
