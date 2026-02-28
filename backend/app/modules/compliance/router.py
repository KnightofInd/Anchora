from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.compliance_schema import ComplianceReportRead
from app.modules.compliance.service import ComplianceService

router = APIRouter()


@router.get("/report/{decision_id}", response_model=ComplianceReportRead)
async def get_compliance_report(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns full compliance report for a decision:
    - Policy check results
    - Violations
    - Risk notes
    """
    return await ComplianceService(db).get_report(decision_id)
