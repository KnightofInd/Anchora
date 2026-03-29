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


class DecisionMeetingNoteCreate(BaseModel):
    meeting_title: Optional[str] = Field(default=None, max_length=255)
    transcript_text: str = Field(..., min_length=20, max_length=20000)
    execution_guidance: Optional[str] = Field(default=None, max_length=5000)
    action_items: list[str] = Field(default_factory=list)


class DecisionMeetingNoteUpdate(BaseModel):
    meeting_title: Optional[str] = Field(default=None, max_length=255)
    transcript_text: Optional[str] = Field(default=None, min_length=20, max_length=20000)
    execution_guidance: Optional[str] = Field(default=None, max_length=5000)
    action_items: Optional[list[str]] = None


class DecisionMeetingNoteRead(BaseModel):
    id: uuid.UUID
    decision_id: uuid.UUID
    meeting_title: Optional[str]
    transcript_text: str
    execution_guidance: Optional[str]
    action_items: list[str]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DecisionRead(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    context: Optional[str]
    reasoning_summary: Optional[str]
    confidence_score: Optional[float]
    risk_score: Optional[float]
    assumptions: list
    ai_model_name: Optional[str]
    ai_model_version: Optional[str]
    ai_prompt_version: Optional[str]
    policy_snapshot: dict = {}
    quality_snapshot: dict = {}
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    references: list[DecisionReferenceRead] = []
    meeting_notes: list[DecisionMeetingNoteRead] = []

    model_config = {"from_attributes": True}
