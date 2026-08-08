import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import met
from app.models import Exercise, TrainingSession
from app.schemas.session import SessionIn


def _exercise_volume(exercise: Exercise) -> float:
    if exercise.sets and exercise.reps and exercise.weight_kg:
        return exercise.sets * exercise.reps * exercise.weight_kg
    return 0.0


def _estimate_kcal(data: SessionIn, weight_kg: float | None) -> float | None:
    if weight_kg is None:
        return None
    minutes: float | None = data.duration_minutes
    if minutes is None:
        exercises_minutes = sum(
            ex.duration_minutes or 0 for ex in data.exercises
        )
        minutes = exercises_minutes or None
    if minutes is None:
        return None
    return met.kcal_burned(met.met_for_discipline(data.discipline), weight_kg, minutes)


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: SessionIn,
    *,
    weight_kg: float | None = None,
) -> TrainingSession:
    exercises = [
        Exercise(**exercise.model_dump(exclude_none=True))
        for exercise in data.exercises
    ]
    for exercise in exercises:
        exercise.volume_kg = _exercise_volume(exercise)

    record = TrainingSession(
        user_id=user_id,
        discipline=data.discipline,
        raw_text=data.raw_text,
        performed_at=data.performed_at,
        duration_minutes=data.duration_minutes,
        note=data.note,
        details=data.details,
        estimated_kcal=_estimate_kcal(data, weight_kg),
        volume_kg=sum(exercise.volume_kg for exercise in exercises),
        exercises=exercises,
    )
    session.add(record)
    await session.commit()
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == record.id)
        .options(selectinload(TrainingSession.exercises))
    )
    return result.scalar_one()


async def list_by_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
) -> list[TrainingSession]:
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.user_id == user_id)
        .options(selectinload(TrainingSession.exercises))
        .order_by(TrainingSession.performed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> TrainingSession | None:
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == session_id, TrainingSession.user_id == user_id)
        .options(selectinload(TrainingSession.exercises))
    )
    return result.scalar_one_or_none()


async def delete_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    record = await get_for_user(session, session_id, user_id)
    if record is None:
        return False
    await session.delete(record)
    await session.commit()
    return True
