from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user import UserCreate, UserRead, TokenResponse, LoginRequest, RefreshRequest
from app.modules.auth.service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    return await AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    tokens = await AuthService(db).login(payload)
    _set_auth_cookies(response, tokens)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    refresh_token = payload.refresh_token
    if not refresh_token and settings.AUTH_COOKIE_ENABLED:
        refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token.")

    tokens = await AuthService(db).refresh(refresh_token)
    _set_auth_cookies(response, tokens)
    return tokens


@router.get("/me", response_model=UserRead)
async def me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).get_me(current_user["user_id"])


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current access token. Client must also clear the cookie."""
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME) if settings.AUTH_COOKIE_ENABLED else None
    await AuthService(db).logout(current_user.get("jti"), current_user["user_id"], refresh_token)
    _clear_auth_cookies(response)


def _set_auth_cookies(response: Response, tokens: TokenResponse) -> None:
    if not settings.AUTH_COOKIE_ENABLED:
        return

    access_exp = int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    refresh_exp = int(settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    common = {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN,
        "path": "/",
    }

    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=tokens.access_token,
        max_age=access_exp,
        expires=access_exp,
        **common,
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=tokens.refresh_token,
        max_age=refresh_exp,
        expires=refresh_exp,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    if not settings.AUTH_COOKIE_ENABLED:
        return

    common = {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": settings.AUTH_COOKIE_SAMESITE,
        "domain": settings.AUTH_COOKIE_DOMAIN,
        "path": "/",
    }

    response.delete_cookie(settings.ACCESS_COOKIE_NAME, **common)
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, **common)
