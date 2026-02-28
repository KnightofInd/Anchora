import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class TaskRead(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    assigned_to: uuid.UUID
    title: str
    description: Optional[str] = None
    status: str
    deadline: Optional[datetime] = None
    approval_notes: dict = Field(default_factory=dict)
    # Derived from approval_notes for frontend convenience
    assigned_role: Optional[str] = None
    step: Optional[int] = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def populate_from_notes(self) -> "TaskRead":
        notes = self.approval_notes or {}
        if self.assigned_role is None:
            self.assigned_role = notes.get("role")
        if self.step is None:
            self.step = notes.get("step")
        return self


class TaskRejectRequest(BaseModel):
    reason: Optional[str] = None


class WorkflowRead(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    status: str
    triggered_by: uuid.UUID
    triggered_at: datetime
    completed_at: Optional[datetime] = None
    tasks: list[TaskRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WorkflowStartRequest(BaseModel):
    decision_id: uuid.UUID
