from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.schemas.user import UserCreate, TokenResponse, LoginRequest
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.audit_engine.logger import audit
from app.config.settings import settings


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
        email = payload.email.strip().lower()
        await self._enforce_login_rate_limits(email)

        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            await self._record_failed_login(email)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")

        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")

        role_name = user.role.name if user.role else "viewer"
        await self._clear_login_failures(email)

        refresh_jti = uuid4().hex
        refresh_token = create_refresh_token(str(user.id), jti=refresh_jti)
        refresh_payload = decode_token(refresh_token) or {}
        refresh_exp = self._to_datetime(refresh_payload.get("exp"))
        await self._persist_refresh_token(
            jti=refresh_jti,
            user_id=str(user.id),
            expires_at=refresh_exp,
        )

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
            refresh_token=refresh_token,
        )

    async def refresh(self, refresh_token: str) -> TokenResponse:
        data = decode_token(refresh_token)
        if not data or data.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        presented_jti = data.get("jti")
        if not presented_jti:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token payload.")

        user_id = data["sub"]

        row = await self.db.execute(
            text(
                """
                SELECT jti, user_id, expires_at, revoked_at, used_at
                FROM refresh_tokens
                WHERE jti = :jti
                """
            ),
            {"jti": presented_jti},
        )
        token_row = row.mappings().first()
        if token_row is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not recognized.")

        now = datetime.now(timezone.utc)
        if token_row["revoked_at"] is not None or token_row["used_at"] is not None:
            await self._revoke_all_refresh_tokens_for_user(token_row["user_id"])
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token reuse detected. Please log in again.",
            )

        expires_at = token_row["expires_at"]
        if expires_at is not None and expires_at <= now:
            await self._revoke_refresh_token_jti(presented_jti)
            await self.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired.")

        if str(token_row["user_id"]) != str(user_id):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token subject mismatch.")

        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

        role_name = user.role.name if user.role else "viewer"

        next_refresh_jti = uuid4().hex
        next_refresh_token = create_refresh_token(str(user.id), jti=next_refresh_jti)
        next_payload = decode_token(next_refresh_token) or {}
        next_exp = self._to_datetime(next_payload.get("exp"))

        await self.db.execute(
            text(
                """
                UPDATE refresh_tokens
                SET revoked_at = :now,
                    used_at = :now,
                    replaced_by_jti = :replaced_by_jti
                WHERE jti = :jti
                """
            ),
            {"now": now, "replaced_by_jti": next_refresh_jti, "jti": presented_jti},
        )
        await self._persist_refresh_token(
            jti=next_refresh_jti,
            user_id=str(user.id),
            expires_at=next_exp,
        )

        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user.id,
            action="refresh_rotated",
            performed_by=user.id,
            metadata={"previous_jti": presented_jti, "new_jti": next_refresh_jti},
        )
        await self.db.commit()

        return TokenResponse(
            access_token=create_access_token(str(user.id), role_name),
            refresh_token=next_refresh_token,
        )

    async def logout(self, jti: str | None, user_id: str, refresh_token: str | None = None) -> None:
        """Revoke the current access token's JTI so it cannot be reused."""
        if not jti:
            pass
        else:
            await self.db.execute(
                text("INSERT INTO revoked_tokens (jti, user_id) VALUES (:jti, :user_id) ON CONFLICT (jti) DO NOTHING"),
                {"jti": jti, "user_id": user_id},
            )

        if refresh_token:
            payload = decode_token(refresh_token)
            refresh_jti = payload.get("jti") if payload else None
            if refresh_jti:
                await self._revoke_refresh_token_jti(refresh_jti)

        await audit.log(
            self.db,
            entity_type="user",
            entity_id=user_id,
            action="logout",
            performed_by=user_id,
        )
        await self.db.commit()

    async def _enforce_login_rate_limits(self, email: str) -> None:
        now = datetime.now(timezone.utc)
        row = await self.db.execute(
            text(
                """
                SELECT failed_attempts, first_failed_at, lock_until
                FROM auth_login_attempts
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        attempt = row.mappings().first()
        if attempt is None:
            return

        lock_until = attempt["lock_until"]
        if lock_until is not None and lock_until > now:
            remaining = int((lock_until - now).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily locked due to failed logins. Retry in {remaining}s.",
            )

        first_failed_at = attempt["first_failed_at"]
        if first_failed_at is not None and now - first_failed_at > timedelta(minutes=settings.LOGIN_ATTEMPT_WINDOW_MINUTES):
            await self._clear_login_failures(email)
            await self.db.commit()

    async def _record_failed_login(self, email: str) -> None:
        now = datetime.now(timezone.utc)
        row = await self.db.execute(
            text(
                """
                SELECT failed_attempts, first_failed_at
                FROM auth_login_attempts
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        attempt = row.mappings().first()

        if attempt is None:
            await self.db.execute(
                text(
                    """
                    INSERT INTO auth_login_attempts (email, failed_attempts, first_failed_at, lock_until, updated_at)
                    VALUES (:email, 1, :now, NULL, :now)
                    """
                ),
                {"email": email, "now": now},
            )
            await self.db.commit()
            return

        first_failed_at = attempt["first_failed_at"]
        failed_attempts = int(attempt["failed_attempts"] or 0)
        if first_failed_at is None or now - first_failed_at > timedelta(minutes=settings.LOGIN_ATTEMPT_WINDOW_MINUTES):
            failed_attempts = 1
            first_failed_at = now
            lock_until = None
        else:
            failed_attempts += 1
            lock_until = None
            if failed_attempts >= settings.LOGIN_MAX_ATTEMPTS:
                lock_until = now + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)

        await self.db.execute(
            text(
                """
                UPDATE auth_login_attempts
                SET failed_attempts = :failed_attempts,
                    first_failed_at = :first_failed_at,
                    lock_until = :lock_until,
                    updated_at = :now
                WHERE email = :email
                """
            ),
            {
                "email": email,
                "failed_attempts": failed_attempts,
                "first_failed_at": first_failed_at,
                "lock_until": lock_until,
                "now": now,
            },
        )
        await self.db.commit()

    async def _clear_login_failures(self, email: str) -> None:
        await self.db.execute(text("DELETE FROM auth_login_attempts WHERE email = :email"), {"email": email})

    async def _persist_refresh_token(self, jti: str, user_id: str, expires_at: datetime | None) -> None:
        await self.db.execute(
            text(
                """
                INSERT INTO refresh_tokens (jti, user_id, issued_at, expires_at)
                VALUES (:jti, :user_id, NOW(), :expires_at)
                ON CONFLICT (jti) DO NOTHING
                """
            ),
            {"jti": jti, "user_id": user_id, "expires_at": expires_at},
        )

    async def _revoke_refresh_token_jti(self, jti: str) -> None:
        await self.db.execute(
            text("UPDATE refresh_tokens SET revoked_at = NOW() WHERE jti = :jti AND revoked_at IS NULL"),
            {"jti": jti},
        )

    async def _revoke_all_refresh_tokens_for_user(self, user_id: str) -> None:
        await self.db.execute(
            text("UPDATE refresh_tokens SET revoked_at = NOW() WHERE user_id = :user_id AND revoked_at IS NULL"),
            {"user_id": user_id},
        )

    def _to_datetime(self, exp: int | float | datetime | None) -> datetime | None:
        if exp is None:
            return None
        if isinstance(exp, datetime):
            return exp.astimezone(timezone.utc)
        return datetime.fromtimestamp(float(exp), tz=timezone.utc)

    async def get_me(self, user_id: str) -> User:
        result = await self.db.execute(
            select(User).options(selectinload(User.role)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user
