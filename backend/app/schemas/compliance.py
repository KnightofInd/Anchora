import uuid
from datetime import datetime
from pydantic import BaseModel


class ComplianceCheckRead(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    policy_id: uuid.UUID
    status: str
    violations: list
    risk_notes: dict
    checked_at: datetime

    model_config = {"from_attributes": True}


class ComplianceReportRead(BaseModel):
    decision_id: uuid.UUID
    checks: list[ComplianceCheckRead]
    overall_status: str   # "pass" if all checks pass, else "fail"
