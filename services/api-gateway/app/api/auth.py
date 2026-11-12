from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import rate_limit
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import verify_password
from app.crud import users
from app.models import User
from app.schemas.auth import LoginIn, RefreshIn, RegisterIn, TokenOut, UserOut
from app.services import auth_sessions

router = APIRouter(prefix="/auth", tags=["auth"])
Db = Annotated[AsyncSession, Depends(get_db)]
Redis = Annotated[aioredis.Redis, Depends(get_redis)]

LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILS_PER_EMAIL = 5
LOGIN_MAX_FAILS_PER_IP = 20
REGISTER_WINDOW_SECONDS = 60 * 60
REGISTER_MAX_PER_IP = 10


def _ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def _too_many(exc: rate_limit.RateLimited) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=str(exc),
        headers={"Retry-After": str(exc.retry_after)},
    )


def _token_out(user: User, tokens: auth_sessions.IssuedTokens) -> TokenOut:
    return TokenOut(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, request: Request, session: Db, redis: Redis) -> TokenOut:
    ip_key = f"register:ip:{_ip(request)}"
    try:
        await rate_limit.check(redis, ip_key, REGISTER_MAX_PER_IP)
    except rate_limit.RateLimited as exc:
        raise _too_many(exc) from exc
    await rate_limit.hit(redis, ip_key, REGISTER_WINDOW_SECONDS)
    existing = await users.get_by_email(session, body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una cuenta con ese email",
        )
    user = await users.create(session, body.email, body.password, body.name.strip())
    tokens = await auth_sessions.start(
        session, user, remember=body.remember, user_agent=_agent(request)
    )
    return _token_out(user, tokens)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, session: Db, redis: Redis) -> TokenOut:
    email_key = f"login:email:{body.email.lower()}"
    ip_key = f"login:ip:{_ip(request)}"
    try:
        await rate_limit.check(redis, email_key, LOGIN_MAX_FAILS_PER_EMAIL)
        await rate_limit.check(redis, ip_key, LOGIN_MAX_FAILS_PER_IP)
    except rate_limit.RateLimited as exc:
        raise _too_many(exc) from exc
    user = await users.get_by_email(session, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        await rate_limit.hit(redis, email_key, LOGIN_WINDOW_SECONDS)
        await rate_limit.hit(redis, ip_key, LOGIN_WINDOW_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    await rate_limit.reset(redis, email_key)
    tokens = await auth_sessions.start(
        session, user, remember=body.remember, user_agent=_agent(request)
    )
    return _token_out(user, tokens)


@router.post("/refresh", response_model=TokenOut)
async def refresh(body: RefreshIn, request: Request, session: Db) -> TokenOut:
    """Cambia un refresh token válido por uno nuevo y un token de acceso (rotación)."""
    try:
        user, tokens = await auth_sessions.rotate(
            session, body.refresh_token, user_agent=_agent(request)
        )
    except auth_sessions.InvalidRefreshToken as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return _token_out(user, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: RefreshIn, session: Db) -> None:
    await auth_sessions.revoke(session, body.refresh_token)


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(session: Db, current_user: Annotated[User, Depends(get_current_user)]) -> None:
    """Cierra la sesión en todos los dispositivos."""
    await auth_sessions.revoke_all(session, current_user)
