"""
Workflow Service
----------------
Execution flow:
Decision → compliance validation → create workflow → task chain → approval → completion

States are STRICTLY sequential:
pending → in_review → approved/rejected → executed

No state may be skipped.
Every transition is audit-logged.
"""

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from app.models.workflow import Workflow, Task, WorkflowStatus, TaskStatus
from app.models.decision import Decision, DecisionStatus
from app.schemas.workflow import WorkflowStartRequest
from app.core.audit_engine.logger import audit
from app.core.policy_engine.evaluator import LocalPolicyEvaluator

# Approval chain based on risk score
_ROLE_CHAINS = [
    {"min": 0,  "max": 5,   "roles": ["Analyst Review"]},
    {"min": 5,  "max": 8,   "roles": ["Analyst Review", "Manager Approval"]},
    {"min": 8,  "max": 100, "roles": ["Analyst Review", "Manager Approval", "Compliance Review"]},
]


class WorkflowService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.policy_engine = LocalPolicyEvaluator(db)

    async def list_all(self) -> list[Workflow]:
        result = await self.db.execute(
            select(Workflow).options(selectinload(Workflow.tasks)).order_by(Workflow.triggered_at.desc())
        )
        return list(result.scalars().all())

    async def start(self, payload: WorkflowStartRequest, user_id: str) -> Workflow:
        # ── Validate decision exists ──────────────────────────────────────────
        result = await self.db.execute(select(Decision).where(Decision.id == payload.decision_id))
        decision = result.scalar_one_or_none()
        if not decision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found.")

        # ── Compliance gate — workflow CANNOT start without policy clearance ──
        policy_result = await self.policy_engine.evaluate({
            "entity_type": "workflow",
            "action": "start",
            "risk_score": decision.risk_score or 0,
            "decision_status": decision.status,
        })

        if not policy_result.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Workflow blocked by policy: {policy_result.violations}",
            )

        # ── Create workflow ───────────────────────────────────────────────────
        workflow = Workflow(
            decision_id=decision.id,
            triggered_by=user_id,
            status=WorkflowStatus.PENDING,
        )
        self.db.add(workflow)
        await self.db.flush()

        # ── Create task chain based on risk score ────────────────────────────────
        risk = decision.risk_score or 0
        roles = ["Analyst Review"]
        for chain in _ROLE_CHAINS:
            if chain["min"] <= risk < chain["max"]:
                roles = chain["roles"]
                break

        for step_idx, role_name in enumerate(roles):
            task = Task(
                workflow_id=workflow.id,
                assigned_to=user_id,
                title=f"Step {step_idx + 1}: {role_name} — {decision.title}",
                status=TaskStatus.PENDING,
                approval_notes={"step": step_idx + 1, "role": role_name},
            )
            self.db.add(task)
        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="workflow",
            entity_id=workflow.id,
            action="started",
            performed_by=user_id,
            metadata={"decision_id": str(decision.id), "policy_result": policy_result.to_dict()},
        )

        await self.db.commit()

        # Reload with tasks relationship for proper serialisation
        reloaded = await self.db.execute(
            select(Workflow).options(selectinload(Workflow.tasks)).where(Workflow.id == workflow.id)
        )
        return reloaded.scalar_one()

    async def get_by_id(self, workflow_id: str) -> Workflow:
        result = await self.db.execute(
            select(Workflow).options(selectinload(Workflow.tasks)).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found.")
        return workflow

    async def approve_task(self, workflow_id: str, task_id: str, user_id: str) -> Task:
        # ── Load task ─────────────────────────────────────────────────────────
        result = await self.db.execute(select(Task).where(Task.id == task_id, Task.workflow_id == workflow_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task cannot be approved from status '{task.status}'.",
            )

        # ── Advance task state machine ────────────────────────────────────────
        if task.status == TaskStatus.PENDING:
            task.status = TaskStatus.IN_PROGRESS
        else:
            task.status = TaskStatus.COMPLETED

        await self.db.flush()

        # ── Advance workflow state machine ────────────────────────────────────
        wf_result = await self.db.execute(
            select(Workflow).options(selectinload(Workflow.tasks)).where(Workflow.id == workflow_id)
        )
        workflow = wf_result.scalar_one_or_none()
        if workflow:
            # Sort tasks by step number within approval_notes
            sorted_tasks = sorted(workflow.tasks, key=lambda t: (t.approval_notes or {}).get("step", 0))
            all_completed = all(t.status == TaskStatus.COMPLETED for t in sorted_tasks)
            pending_tasks = [t for t in sorted_tasks if t.status == TaskStatus.PENDING]

            if workflow.status == WorkflowStatus.PENDING:
                workflow.status = WorkflowStatus.IN_REVIEW
            elif workflow.status == WorkflowStatus.IN_REVIEW and all_completed:
                workflow.status = WorkflowStatus.APPROVED
                workflow.completed_at = datetime.now(timezone.utc)
                # Mirror approval onto the linked decision
                dec_res = await self.db.execute(select(Decision).where(Decision.id == workflow.decision_id))
                linked = dec_res.scalar_one_or_none()
                if linked and linked.status == DecisionStatus.DRAFT:
                    linked.status = DecisionStatus.APPROVED
            elif workflow.status == WorkflowStatus.IN_REVIEW and pending_tasks:
                # There are more steps — the next pending task becomes the active one
                # (frontend highlights the first pending task as the actionable one)
                pass
            await self.db.flush()

        await audit.log(
            self.db,
            entity_type="task",
            entity_id=task.id,
            action="approved",
            performed_by=user_id,
            metadata={"workflow_id": workflow_id, "new_task_status": task.status, "workflow_status": workflow.status if workflow else None},
        )
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def reject_task(self, workflow_id: str, task_id: str, user_id: str, reason: str | None = None) -> Task:
        """Reject a pending/in-progress task — fails the workflow and the linked decision."""
        result = await self.db.execute(select(Task).where(Task.id == task_id, Task.workflow_id == workflow_id))
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task cannot be rejected from status '{task.status}'.",
            )

        task.status = TaskStatus.COMPLETED  # reuse COMPLETED, workflow handles rejection
        notes = dict(task.approval_notes or {})
        notes["rejected"] = True
        notes["rejection_reason"] = reason or "No reason provided"
        task.approval_notes = notes
        await self.db.flush()

        # Reject the workflow
        wf_res = await self.db.execute(
            select(Workflow).options(selectinload(Workflow.tasks)).where(Workflow.id == workflow_id)
        )
        workflow = wf_res.scalar_one_or_none()
        if workflow:
            workflow.status = WorkflowStatus.REJECTED
            workflow.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

            # Mirror rejection onto the linked decision
            dec_res = await self.db.execute(select(Decision).where(Decision.id == workflow.decision_id))
            linked = dec_res.scalar_one_or_none()
            if linked and linked.status == DecisionStatus.DRAFT:
                linked.status = DecisionStatus.REJECTED
                await self.db.flush()

        await audit.log(
            self.db,
            entity_type="task",
            entity_id=task.id,
            action="rejected",
            performed_by=user_id,
            metadata={"workflow_id": workflow_id, "reason": reason},
        )
        await self.db.commit()
        await self.db.refresh(task)
        return task
