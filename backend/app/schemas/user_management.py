from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class AdminUserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    role_id: uuid.UUID
    role_name: str
    created_at: datetime


class AdminUserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=128)
    password: str = Field(..., min_length=8, max_length=128)
    role_id: uuid.UUID
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=128)
    role_id: uuid.UUID | None = None
    is_active: bool | None = None
