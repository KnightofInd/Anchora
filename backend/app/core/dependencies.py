from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token

from app.config.settings import settings

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Validates JWT and returns the current user dict.
    Also checks the token JTI against the revoked_tokens blocklist.
    """
    token = None
    if credentials is not None:
        token = credentials.credentials
    elif settings.AUTH_COOKIE_ENABLED:
        token = request.cookies.get(settings.ACCESS_COOKIE_NAME)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    # Check token blocklist via raw SQL (avoids model import cycle)
    jti = payload.get("jti")
    if jti:
        from sqlalchemy import text
        result = await db.execute(text("SELECT 1 FROM revoked_tokens WHERE jti = :jti"), {"jti": jti})
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked. Please log in again.",
            )

    return {"user_id": payload["sub"], "role": payload.get("role"), "jti": jti}


def require_role(*allowed_roles: str):
    """
    Factory that returns a dependency enforcing specific roles.
    Usage: Depends(require_role("admin", "analyst"))
    """
    async def role_checker(current_user: dict = Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user['role']}' is not permitted for this action.",
            )
        return current_user
    return role_checker
