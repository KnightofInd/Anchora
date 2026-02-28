from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.workflow import WorkflowRead, WorkflowStartRequest, TaskRead, TaskRejectRequest
from app.modules.workflow.service import WorkflowService

router = APIRouter()


@router.get("/", response_model=list[WorkflowRead])
async def list_workflows(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all workflows."""
    return await WorkflowService(db).list_all()


@router.post("/", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    payload: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Triggers workflow for a decision.
    Runs compliance check before creating task chain.
    """
    return await WorkflowService(db).start(payload, current_user["user_id"])


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await WorkflowService(db).get_by_id(workflow_id)


@router.post("/{workflow_id}/tasks/{task_id}/approve", response_model=TaskRead)
async def approve_task(
    workflow_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return await WorkflowService(db).approve_task(workflow_id, task_id, current_user["user_id"])


@router.post("/{workflow_id}/tasks/{task_id}/reject", response_model=TaskRead)
async def reject_task(
    workflow_id: str,
    task_id: str,
    payload: TaskRejectRequest = TaskRejectRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Reject a task — fails the entire workflow and marks the decision rejected."""
    return await WorkflowService(db).reject_task(workflow_id, task_id, current_user["user_id"], payload.reason)
