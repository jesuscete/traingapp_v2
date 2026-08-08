import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models import User


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
