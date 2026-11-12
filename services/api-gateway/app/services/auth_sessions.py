"""Sesiones con token de acceso corto (JWT) y refresh token rotatorio guardado como hash."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models import AuthSession, User


class InvalidRefreshToken(Exception):
    """Refresh token inexistente, caducado o revocado."""


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int  # segundos de vida del token de acceso


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _lifetime(remember: bool) -> timedelta:
    if remember:
        return timedelta(days=settings.remember_token_expire_days)
    return timedelta(hours=settings.session_refresh_hours)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def _new_refresh(
    session: AsyncSession,
    user: User,
    *,
    remember: bool,
    family_id: uuid.UUID,
    user_agent: str | None,
) -> IssuedTokens:
    refresh = secrets.token_urlsafe(48)
    session.add(
        AuthSession(
            user_id=user.id,
            family_id=family_id,
            token_hash=_hash(refresh),
            remember=remember,
            user_agent=(user_agent or "")[:200] or None,
            expires_at=datetime.now(UTC) + _lifetime(remember),
        )
    )
    await session.commit()
    return IssuedTokens(
        access_token=create_access_token(str(user.id), user.token_version),
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def start(
    session: AsyncSession, user: User, *, remember: bool, user_agent: str | None
) -> IssuedTokens:
    return await _new_refresh(
        session, user, remember=remember, family_id=uuid.uuid4(), user_agent=user_agent
    )


async def _revoke_family(session: AsyncSession, family_id: uuid.UUID) -> None:
    await session.execute(
        update(AuthSession)
        .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    await session.commit()


async def rotate(
    session: AsyncSession, refresh_token: str, *, user_agent: str | None
) -> tuple[User, IssuedTokens]:
    row = await session.scalar(
        select(AuthSession).where(AuthSession.token_hash == _hash(refresh_token))
    )
    if row is None:
        raise InvalidRefreshToken("Sesión no válida")
    if row.revoked_at is not None:
        # Un token ya usado vuelve a aparecer: posible robo. Se corta toda la sesión.
        await _revoke_family(session, row.family_id)
        raise InvalidRefreshToken("Sesión revocada")
    if _aware(row.expires_at) <= datetime.now(UTC):
        raise InvalidRefreshToken("Sesión caducada")
    user = await session.get(User, row.user_id)
    if user is None:
        raise InvalidRefreshToken("Usuario no encontrado")
    row.revoked_at = datetime.now(UTC)
    tokens = await _new_refresh(
        session, user, remember=row.remember, family_id=row.family_id, user_agent=user_agent
    )
    return user, tokens


async def revoke(session: AsyncSession, refresh_token: str) -> None:
    row = await session.scalar(
        select(AuthSession).where(AuthSession.token_hash == _hash(refresh_token))
    )
    if row is not None:
        await _revoke_family(session, row.family_id)


async def revoke_all(session: AsyncSession, user: User) -> None:
    """Cierra todas las sesiones: revoca los refresh e invalida los tokens de acceso vivos."""
    await session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    user.token_version += 1
    await session.commit()
