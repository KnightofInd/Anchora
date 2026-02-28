from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.decision import DecisionCreate, DecisionRead, DecisionStatusUpdate
from app.modules.decision.service import DecisionService

router = APIRouter()


@router.get("/", response_model=list[DecisionRead])
async def list_decisions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all decisions, newest first."""
    return await DecisionService(db).list_all()


@router.post("/", response_model=DecisionRead, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Creates a decision object:
    1. Retrieves relevant documents via semantic search
    2. Calls Gemini for recommendation + reasoning
    3. Runs policy engine (compliance pre-check) — blocks on hard violations
    4. Stores decision with full traceability (document refs, AI metadata)
    5. Logs audit entry
    """
    return await DecisionService(db).create(
        payload,
        user_id=current_user["user_id"],
        user_role=current_user.get("role", "analyst"),
    )


@router.get("/{decision_id}", response_model=DecisionRead)
async def get_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get a single decision with all document references."""
    return await DecisionService(db).get_by_id(decision_id)


@router.patch("/{decision_id}/status", response_model=DecisionRead)
async def update_decision_status(
    decision_id: str,
    payload: DecisionStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
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
