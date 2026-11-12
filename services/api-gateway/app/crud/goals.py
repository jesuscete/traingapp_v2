import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserGoal


async def list_goals(session: AsyncSession, user_id: uuid.UUID) -> list[UserGoal]:
    """Metas del usuario: activas primero, la principal delante y por fecha objetivo."""
    rows = await session.scalars(
        select(UserGoal)
        .where(UserGoal.user_id == user_id)
        .order_by(
            UserGoal.done,
            UserGoal.is_primary.desc(),
            UserGoal.target_date.is_(None),
            UserGoal.target_date,
        )
    )
    return list(rows)
