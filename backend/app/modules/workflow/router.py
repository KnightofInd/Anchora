from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.idempotency import IdempotencyService
from app.core.dependencies import require_role
from app.schemas.workflow import WorkflowRead, WorkflowStartRequest, TaskRead, TaskRejectRequest
from app.modules.workflow.service import WorkflowService

router = APIRouter()


@router.get("/", response_model=list[WorkflowRead])
async def list_workflows(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("triggered_at", pattern="^(triggered_at|completed_at|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst", "auditor")),
):
    """List workflows with standardized pagination, sorting, and optional status filter."""
    return await WorkflowService(db).list_paged(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        status_filter=status_filter,
    )


@router.post("/", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def start_workflow(
    payload: WorkflowStartRequest,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    """
    Triggers workflow for a decision.
    Runs compliance check before creating task chain.
    """
    user_id = str(current_user["user_id"])
    if idempotency_key:
        idem = IdempotencyService(db)
        request_hash = idem.build_request_hash(payload.model_dump(mode="json"))
        replay = await idem.get_replay(
            user_id=user_id,
            endpoint=request.url.path,
            key=idempotency_key,
            request_hash=request_hash,
        )
        if replay:
            status_code, body = replay
            return JSONResponse(status_code=status_code, content=body, headers={"Idempotent-Replayed": "true"})

    workflow = await WorkflowService(db).start(payload, current_user["user_id"])

    if idempotency_key:
        encoded = jsonable_encoder(workflow)
        idem = IdempotencyService(db)
        request_hash = idem.build_request_hash(payload.model_dump(mode="json"))
        await idem.save(
            user_id=user_id,
            endpoint=request.url.path,
            key=idempotency_key,
            request_hash=request_hash,
            status_code=status.HTTP_201_CREATED,
            response_body=encoded,
        )
        await db.commit()

    return workflow


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst", "auditor")),
):
    return await WorkflowService(db).get_by_id(workflow_id)


@router.post("/{workflow_id}/tasks/{task_id}/approve", response_model=TaskRead)
async def approve_task(
    workflow_id: str,
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    return await WorkflowService(db).approve_task(workflow_id, task_id, current_user["user_id"])


@router.post("/{workflow_id}/tasks/{task_id}/reject", response_model=TaskRead)
async def reject_task(
    workflow_id: str,
    task_id: str,
    payload: TaskRejectRequest = TaskRejectRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    """Reject a task — fails the entire workflow and marks the decision rejected."""
    return await WorkflowService(db).reject_task(workflow_id, task_id, current_user["user_id"], payload.reason)
