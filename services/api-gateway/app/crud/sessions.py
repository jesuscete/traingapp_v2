import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import kcal as kcal_analytics
from app.models import Exercise, TrainingSession
from app.schemas.session import SessionIn


def _exercise_volume(exercise: Exercise) -> float:
    if exercise.sets and exercise.reps and exercise.weight_kg:
        return exercise.sets * exercise.reps * exercise.weight_kg
    return 0.0


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _estimate_kcal(
    data: SessionIn, weight_kg: float | None
) -> tuple[float | None, dict[str, object]]:
    minutes: float | None = data.duration_minutes
    if minutes is None:
        exercises_minutes = sum(ex.duration_minutes or 0 for ex in data.exercises)
        minutes = exercises_minutes or None

    details = dict(data.details or {})
    input_ = kcal_analytics.SessionKcalInput(
        discipline=data.discipline,
        weight_kg=weight_kg,
        duration_minutes=int(minutes) if minutes is not None else None,
        rpe=_as_int(details.get("rpe")),
        avg_heart_rate=_as_float(details.get("avgHeartRate")),
        workout_type=_as_str(details.get("workoutType")),
        distance_meters=data.distance_meters,
        exercises=tuple(
            kcal_analytics.ExerciseInput(
                name=ex.name,
                weight_kg=ex.weight_kg,
                sets=ex.sets,
                reps=ex.reps,
                rest_seconds=_as_int((ex.details or {}).get("restSeconds")),
            )
            for ex in data.exercises
        ),
    )
    estimate = kcal_analytics.estimate(input_)
    details["kcal_confidence"] = estimate.confidence
    details["kcal_confidence_level"] = estimate.confidence_level
    details["kcal_factors"] = estimate.factors
    return estimate.kcal, details


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

    estimated_kcal, enriched_details = _estimate_kcal(data, weight_kg)

    record = TrainingSession(
        user_id=user_id,
        discipline=data.discipline,
        raw_text=data.raw_text,
        performed_at=data.performed_at,
        duration_minutes=data.duration_minutes,
        note=data.note,
        details=enriched_details,
        estimated_kcal=estimated_kcal,
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
