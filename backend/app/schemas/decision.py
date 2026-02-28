import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DecisionCreate(BaseModel):
    title: str
    description: Optional[str] = None
    context: str = Field(..., description="Context text used to generate AI recommendation")


class DecisionReferenceRead(BaseModel):
    id: uuid.UUID
    document_id: Optional[uuid.UUID]
    data_source: Optional[str]
    reference_type: str

    model_config = {"from_attributes": True}


class DecisionStatusUpdate(BaseModel):
    status: str  # approved | rejected | executed
    notes: Optional[str] = None


class DecisionRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    reasoning_summary: Optional[str]
    confidence_score: Optional[float]
    risk_score: Optional[float]
    assumptions: list
    ai_model_name: Optional[str]
    ai_model_version: Optional[str]
    ai_prompt_version: Optional[str]
    status: str
    created_by: uuid.UUID
    created_at: datetime
    references: list[DecisionReferenceRead] = []

    model_config = {"from_attributes": True}
