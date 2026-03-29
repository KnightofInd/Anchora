from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit_engine.logger import audit
from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.schemas.user_management import AdminUserCreate, AdminUserRead, AdminUserUpdate, RoleRead


class UserManagementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_roles(self) -> list[RoleRead]:
        result = await self.db.execute(select(Role).order_by(Role.name.asc()))
        roles = list(result.scalars().all())
        return [RoleRead.model_validate(role) for role in roles]

    async def list_users(self) -> list[AdminUserRead]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role))
            .order_by(User.created_at.desc())
        )
        users = list(result.scalars().all())
        return [
            AdminUserRead(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                is_active=user.is_active,
                role_id=user.role_id,
                role_name=user.role.name if user.role else "unknown",
                created_at=user.created_at,
            )
            for user in users
        ]

    async def create_user(self, payload: AdminUserCreate, actor_user_id: str) -> AdminUserRead:
        existing = await self.db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

        role = await self.db.execute(select(Role).where(Role.id == payload.role_id))
        role_obj = role.scalar_one_or_none()
        if role_obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role_id=payload.role_id,
            is_active=payload.is_active,
        )
        self.db.add(user)
        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user.id,
            action="admin_created_user",
            performed_by=actor_user_id,
            metadata={
                "email": user.email,
                "role": role_obj.name,
                "is_active": user.is_active,
            },
        )

        await self.db.commit()
        await self.db.refresh(user)
        return AdminUserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_id=user.role_id,
            role_name=role_obj.name,
            created_at=user.created_at,
        )

    async def update_user(self, user_id: uuid.UUID, payload: AdminUserUpdate, actor_user_id: str) -> AdminUserRead:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        updated_fields: dict[str, str | bool] = {}

        if payload.full_name is not None:
            user.full_name = payload.full_name
            updated_fields["full_name"] = payload.full_name

        if payload.is_active is not None:
            user.is_active = payload.is_active
            updated_fields["is_active"] = payload.is_active

        if payload.role_id is not None:
            role = await self.db.execute(select(Role).where(Role.id == payload.role_id))
            role_obj = role.scalar_one_or_none()
            if role_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found.")
            user.role_id = payload.role_id
            user.role = role_obj
            updated_fields["role"] = role_obj.name

        if updated_fields:
            await audit.log(
                self.db,
                entity_type="user",
                entity_id=user.id,
                action="admin_updated_user",
                performed_by=actor_user_id,
                metadata=updated_fields,
            )

        await self.db.commit()
        await self.db.refresh(user)

        current_role_name = user.role.name if user.role else "unknown"
        return AdminUserRead(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            role_id=user.role_id,
            role_name=current_role_name,
            created_at=user.created_at,
        )
