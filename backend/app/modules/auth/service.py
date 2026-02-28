from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, TokenResponse, LoginRequest, RefreshRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.audit_engine.logger import audit


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: UserCreate) -> User:
        existing = await self.db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered.")

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role_id=payload.role_id,
        )
        self.db.add(user)
        await self.db.flush()

        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user.id,
            action="registered",
            performed_by=user.id,
            metadata={"email": user.email},
        )
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, payload: LoginRequest) -> TokenResponse:
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.email == payload.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")

        role_name = user.role.name if user.role else "viewer"

        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user.id,
            action="login",
            performed_by=user.id,
        )
        await self.db.commit()

        return TokenResponse(
            access_token=create_access_token(str(user.id), role_name),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        data = decode_token(payload.refresh_token)
        if not data or data.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )
        user_id = data["sub"]
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

        role_name = user.role.name if user.role else "viewer"
        return TokenResponse(
            access_token=create_access_token(str(user.id), role_name),
            refresh_token=create_refresh_token(str(user.id)),
        )

    async def logout(self, jti: str | None, user_id: str) -> None:
        """Revoke the current access token's JTI so it cannot be reused."""
        if not jti:
            return
        from sqlalchemy import text
        await self.db.execute(
            text("INSERT INTO revoked_tokens (jti, user_id) VALUES (:jti, :user_id) ON CONFLICT (jti) DO NOTHING"),
            {"jti": jti, "user_id": user_id},
        )
        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user_id,
            action="logout",
            performed_by=user_id,
        )
        await self.db.commit()

    async def get_me(self, user_id: str) -> User:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user
