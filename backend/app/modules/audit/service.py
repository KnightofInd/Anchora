"""
Audit Service
-------------
Provides structured access to the immutable audit log.
The trace_decision method aggregates the FULL lifecycle:
  decision → compliance → workflow → tasks
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.audit import AuditLog
from app.models.workflow import Workflow, Task


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_logs(
        self,
        entity_type: str | None = None,
        entity_id: str | None = None,
        performed_by: str | None = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "timestamp",
        sort_order: str = "desc",
    ) -> list[AuditLog]:
        sort_columns = {
            "timestamp": AuditLog.timestamp,
            "entity_type": AuditLog.entity_type,
            "action": AuditLog.action,
        }
        column = sort_columns.get(sort_by, AuditLog.timestamp)
        order_expr = column.asc() if sort_order == "asc" else column.desc()

        query = select(AuditLog)
        if entity_type:
            query = query.where(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        if performed_by:
            query = query.where(AuditLog.performed_by == performed_by)
        result = await self.db.execute(
            query
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def trace_decision(self, decision_id: str) -> list[AuditLog]:
        """
        Returns the full ordered audit trail for a decision:
        - decision-level events (created, compliance_checked)
        - workflow-level events (started)
        - task-level events (approved)
        """
        ids_to_trace: set[str] = {decision_id}

        # Collect all workflow IDs for this decision
        wf_result = await self.db.execute(
            select(Workflow.id).where(Workflow.decision_id == decision_id)
        )
        workflow_ids = [str(wid) for wid in wf_result.scalars().all()]
        ids_to_trace.update(workflow_ids)

        # Collect all task IDs for those workflows
        if workflow_ids:
            task_result = await self.db.execute(
                select(Task.id).where(Task.workflow_id.in_(workflow_ids))
            )
            task_ids = [str(tid) for tid in task_result.scalars().all()]
            ids_to_trace.update(task_ids)

        # Fetch all audit logs for all collected IDs
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.entity_id.in_(list(ids_to_trace)))
            .order_by(AuditLog.timestamp.asc())
        )
        return list(result.scalars().all())
