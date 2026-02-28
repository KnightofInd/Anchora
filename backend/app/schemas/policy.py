import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rule_definition: dict


class PolicyRead(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    is_active: bool
    rule_definition: dict
    created_at: datetime

    model_config = {"from_attributes": True}
