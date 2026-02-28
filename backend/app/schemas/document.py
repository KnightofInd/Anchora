import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: uuid.UUID
    title: str
    version: int
    source: Optional[str]
    file_hash: Optional[str]
    meta: dict
    uploaded_by: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    storage_path: str
    message: str
