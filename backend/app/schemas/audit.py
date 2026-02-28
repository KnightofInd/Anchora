import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AuditLogRead(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: str
    action: str
    performed_by: str
    timestamp: datetime
    meta: Optional[dict] = Field(default_factory=dict)

    model_config = {"from_attributes": True}
