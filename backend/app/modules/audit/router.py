from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.schemas.audit import AuditLogRead
from app.modules.audit.service import AuditService

router = APIRouter()


@router.get("/", response_model=list[AuditLogRead])
async def list_audit_logs(
    entity_type: str | None = Query(None),
    entity_id:   str | None = Query(None),
    performed_by: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "auditor")),
):
    """
    Retrieves immutable audit logs.
    Supports filtering by entity_type, entity_id, performed_by.
    Only accessible by admin and auditor roles.
    """
    return await AuditService(db).list_logs(entity_type, entity_id, performed_by)


@router.get("/trace/{decision_id}", response_model=list[AuditLogRead])
async def trace_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "auditor")),
):
    """
    Full lifecycle audit trace for a decision.
    Returns all audit records across:
      - decision created / compliance_checked
      - workflow started
      - task approved

    This is the critical Phase 7 acceptance test endpoint.
    """
    return await AuditService(db).trace_decision(decision_id)
