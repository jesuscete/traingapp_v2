import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import TrainingSession, WorkoutExercise, WorkoutSet

_LOADS = (
    selectinload(TrainingSession.exercises),
    selectinload(TrainingSession.workout_exercises)
    .selectinload(WorkoutExercise.sets)
    .selectinload(WorkoutSet.entries),
)


async def sessions_in_range(
    session: AsyncSession,
    user_id: uuid.UUID,
    start: datetime,
    end: datetime | None = None,
) -> list[TrainingSession]:
    query = (
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.performed_at >= start,
        )
        .options(*_LOADS)
        .order_by(TrainingSession.performed_at)
    )
    if end is not None:
        query = query.where(TrainingSession.performed_at < end)
    result = await session.execute(query)
    return list(result.scalars().all())
