import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User
from app.schemas.auth import ProfileIn


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def create(
    session: AsyncSession, email: str, password: str, name: str
) -> User:
    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        name=name,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


_PROFILE_FIELDS = (
    "name",
    "weight_kg",
    "height_cm",
    "birth_year",
    "sex",
    "goal",
    "sports",
    "body_fat_pct",
    "fitness_level",
    "weekly_availability",
    "injuries",
    "goals",
)


async def update_profile(session: AsyncSession, user: User, body: ProfileIn) -> User:
    for field in _PROFILE_FIELDS:
        value = getattr(body, field)
        if value is not None:
            setattr(user, field, value)
    await session.commit()
    await session.refresh(user)
    return user


async def update_email(session: AsyncSession, user: User, email: str) -> User:
    user.email = email.lower()
    await session.commit()
    await session.refresh(user)
    return user


async def update_password(session: AsyncSession, user: User, new_password: str) -> User:
    user.hashed_password = hash_password(new_password)
    await session.commit()
    await session.refresh(user)
    return user
