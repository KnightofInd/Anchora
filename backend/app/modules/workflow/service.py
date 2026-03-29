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

    async def list_paged(
        self,
        *,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
        status_filter: str | None = None,
    ) -> list[Workflow]:
        sort_columns = {
            "triggered_at": Workflow.triggered_at,
            "completed_at": Workflow.completed_at,
            "status": Workflow.status,
        }
        column = sort_columns.get(sort_by, Workflow.triggered_at)
        order_expr = column.asc() if sort_order == "asc" else column.desc()

        query = select(Workflow).options(selectinload(Workflow.tasks))
        if status_filter:
            query = query.where(Workflow.status == status_filter)

        result = await self.db.execute(
            query
            .order_by(order_expr)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def start(self, payload: WorkflowStartRequest, user_id: str) -> Workflow:
        # ── Validate decision exists ──────────────────────────────────────────
        result = await self.db.execute(select(Decision).where(Decision.id == payload.decision_id))
        decision = result.scalar_one_or_none()
        if not decision:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found.")

        # ── Guard: only DRAFT decisions may enter a workflow ─────────────────
        if decision.status != DecisionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot start a workflow for a '{decision.status}' decision. Only DRAFT decisions are eligible.",
            )

        # ── Guard: no active workflow may already exist for this decision ─────
        existing_wf_result = await self.db.execute(
            select(Workflow).where(
                Workflow.decision_id == decision.id,
                Workflow.status.in_([
                    WorkflowStatus.PENDING,
                    WorkflowStatus.IN_REVIEW,
                    WorkflowStatus.APPROVED,
                ]),
            )
        )
        if existing_wf_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active workflow already exists for this decision.",
            )

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
        # ── Load task with row-level lock (prevents double-approval races) ────
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id, Task.workflow_id == workflow_id)
            .with_for_update()
        )
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")

        if task.status not in (TaskStatus.PENDING, TaskStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Task cannot be approved from status '{task.status}'.",
            )

        # ── Sequential step enforcement ───────────────────────────────────────
        # Before activating a PENDING task, verify all prior steps are completed.
        if task.status == TaskStatus.PENDING:
            current_step = (task.approval_notes or {}).get("step", 0)
            if current_step > 1:
                prior_result = await self.db.execute(
                    select(Task).where(Task.workflow_id == workflow_id)
                )
                all_tasks = list(prior_result.scalars().all())
                incomplete_prior = [
                    t for t in all_tasks
                    if (t.approval_notes or {}).get("step", 0) < current_step
                    and t.status != TaskStatus.COMPLETED
                ]
                if incomplete_prior:
                    prior_steps = sorted(
                        {
                            int(step)
                            for t in incomplete_prior
                            for step in [(t.approval_notes or {}).get("step")]
                            if isinstance(step, int)
                        }
                    )
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Cannot start step {current_step}: "
                            f"step(s) {prior_steps} must be completed first."
                        ),
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
        result = await self.db.execute(
            select(Task)
            .where(Task.id == task_id, Task.workflow_id == workflow_id)
            .with_for_update()
        )
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
