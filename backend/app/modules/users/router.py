from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.modules.users.service import UserManagementService
from app.schemas.user_management import AdminUserCreate, AdminUserRead, AdminUserUpdate, RoleRead

router = APIRouter()


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    return await UserManagementService(db).list_roles()


@router.get("/users", response_model=list[AdminUserRead])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    return await UserManagementService(db).list_users()


@router.post("/users", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    return await UserManagementService(db).create_user(payload, actor_user_id=str(current_user["user_id"]))


@router.patch("/users/{user_id}", response_model=AdminUserRead)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(require_role("admin")),
):
    return await UserManagementService(db).update_user(
        user_id,
        payload,
        actor_user_id=str(current_user["user_id"]),
    )
