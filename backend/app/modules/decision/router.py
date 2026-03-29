from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.idempotency import IdempotencyService
from app.core.database import get_db
from app.core.dependencies import require_role
from app.schemas.decision import (
    DecisionCreate,
    DecisionMeetingNoteCreate,
    DecisionMeetingNoteRead,
    DecisionMeetingNoteUpdate,
    DecisionRead,
    DecisionStatusUpdate,
)
from app.modules.decision.service import DecisionService

router = APIRouter()


@router.get("/", response_model=list[DecisionRead])
async def list_decisions(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", pattern="^(created_at|title|risk_score|confidence_score|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst", "auditor", "viewer")),
):
    """List decisions with standardized pagination, sorting, and optional status filter."""
    return await DecisionService(db).list_paged(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
        status_filter=status_filter,
    )


@router.post("/", response_model=DecisionRead, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionCreate,
    request: Request,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    """
    Creates a decision object:
    1. Retrieves relevant documents via semantic search
    2. Calls Gemini for recommendation + reasoning
    3. Runs policy engine (compliance pre-check) — blocks on hard violations
    4. Stores decision with full traceability (document refs, AI metadata)
    5. Logs audit entry
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

    decision = await DecisionService(db).create(
        payload,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "analyst"),
    )

    if idempotency_key:
        encoded = jsonable_encoder(decision)
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

    return decision


@router.get("/{decision_id}", response_model=DecisionRead)
async def get_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst", "auditor", "viewer")),
):
    """Get a single decision with all document references."""
    return await DecisionService(db).get_by_id(decision_id)


@router.patch("/{decision_id}/status", response_model=DecisionRead)
async def update_decision_status(
    decision_id: str,
    payload: DecisionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    """
    Transition a decision status.
    Valid: draft → approved | rejected; approved → executed.
    Every transition is audit-logged and immutable.
    """
    return await DecisionService(db).update_status(
        decision_id,
        new_status=payload.status,
        user_id=current_user["user_id"],
        notes=payload.notes,
    )


@router.get("/{decision_id}/meeting-notes", response_model=list[DecisionMeetingNoteRead])
async def list_decision_meeting_notes(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst", "auditor", "viewer")),
):
    return await DecisionService(db).list_meeting_notes(decision_id)


@router.post("/{decision_id}/meeting-notes", response_model=DecisionMeetingNoteRead, status_code=status.HTTP_201_CREATED)
async def create_decision_meeting_note(
    decision_id: str,
    payload: DecisionMeetingNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    return await DecisionService(db).add_meeting_note(
        decision_id=decision_id,
        payload=payload,
        user_id=current_user["user_id"],
    )


@router.patch("/{decision_id}/meeting-notes/{note_id}", response_model=DecisionMeetingNoteRead)
async def update_decision_meeting_note(
    decision_id: str,
    note_id: str,
    payload: DecisionMeetingNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin", "analyst")),
):
    return await DecisionService(db).update_meeting_note(
        decision_id=decision_id,
        note_id=note_id,
        payload=payload,
        user_id=current_user["user_id"],
    )
