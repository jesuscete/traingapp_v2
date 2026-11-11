"""Alta de sesiones con un único modelo para fuerza (ADR-001).

Las sesiones de gimnasio que llegan en formato plano (`SessionIn`) se convierten
al modelo `workout_exercise/set/set_entry`; el resto sigue el camino genérico.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import gym as gym_crud
from app.crud import sessions as sessions_crud
from app.crud import users as users_crud
from app.models import TrainingSession
from app.schemas.gym import GymSessionIn, SetEntryIn, WorkoutExerciseIn, WorkoutSetIn
from app.schemas.session import ExerciseIn, SessionIn

STRENGTH_DISCIPLINES = frozenset({"gym"})
REST_KEYS = ("restSeconds", "rest_seconds", "descanso")


def _int_in_range(value: object, low: int, high: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = round(value)
    return number if low <= number <= high else None


def _rest_seconds(details: dict[str, object]) -> int | None:
    for key in REST_KEYS:
        rest = _int_in_range(details.get(key), 0, 3600)
        if rest is not None:
            return rest
    return None


def _entry(exercise: ExerciseIn, rpe: int | None) -> SetEntryIn:
    duration = (
        exercise.duration_minutes * 60 if exercise.duration_minutes is not None else None
    )
    return SetEntryIn(
        entry_order=0,
        reps=exercise.reps,
        weight=exercise.weight_kg,
        duration_seconds=duration,
        distance_meters=exercise.distance_meters,
        rpe=rpe,
    )


def _workout_exercise(exercise: ExerciseIn, order_index: int) -> WorkoutExerciseIn:
    sets_count = exercise.sets or 1
    details = exercise.details or {}
    rpe = _int_in_range(details.get("rpe"), 1, 10)
    rest = _rest_seconds(details)
    return WorkoutExerciseIn(
        name=exercise.name,
        order_index=order_index,
        sets=[
            WorkoutSetIn(set_number=n, rest_seconds=rest, entries=[_entry(exercise, rpe)])
            for n in range(1, sets_count + 1)
        ],
    )


def to_gym_session_in(body: SessionIn) -> GymSessionIn | None:
    """Devuelve el equivalente en modelo gym, o None si no es una sesión de fuerza."""
    if body.discipline not in STRENGTH_DISCIPLINES or not body.exercises:
        return None
    details = dict(body.details or {})
    if body.distance_meters is not None:
        details["distanceMeters"] = body.distance_meters
    return GymSessionIn(
        raw_text=body.raw_text,
        performed_at=body.performed_at,
        duration_minutes=body.duration_minutes,
        intensity=body.intensity,
        fatigue=body.fatigue,
        note=body.note,
        routine_day_id=body.routine_day_id,
        details=details or None,
        exercises=[_workout_exercise(ex, i) for i, ex in enumerate(body.exercises)],
    )


async def create_session(
    session: AsyncSession,
    user_id: uuid.UUID,
    body: SessionIn,
    *,
    weight_kg: float | None,
) -> TrainingSession:
    gym_in = to_gym_session_in(body)
    if gym_in is not None:
        return await gym_crud.create_gym(session, user_id, gym_in, weight_kg=weight_kg)
    return await sessions_crud.create(session, user_id, body, weight_kg=weight_kg)


def _legacy_to_session_in(record: TrainingSession) -> SessionIn:
    return SessionIn.model_validate(
        {
            "discipline": record.discipline,
            "raw_text": record.raw_text or "sesión migrada",
            "performed_at": record.performed_at,
            "duration_minutes": record.duration_minutes,
            "intensity": record.intensity,
            "fatigue": record.fatigue,
            "note": record.note,
            "routine_day_id": record.routine_day_id,
            "details": record.details,
            "exercises": [
                {
                    "name": ex.name,
                    "sets": ex.sets,
                    "reps": ex.reps,
                    "weight_kg": ex.weight_kg,
                    "duration_minutes": ex.duration_minutes,
                    "distance_meters": ex.distance_meters,
                    "details": ex.details,
                }
                for ex in record.exercises
            ],
        }
    )


async def migrate_legacy_strength_sessions(session: AsyncSession) -> int:
    """Pasa las sesiones de fuerza guardadas en `exercises` al modelo gym.

    Idempotente: solo toca sesiones de fuerza con ejercicios planos y sin
    `workout_exercises`. Conserva `created_at`; el id de la sesión cambia.
    """
    legacy = await sessions_crud.legacy_strength_sessions(session, STRENGTH_DISCIPLINES)
    for record in legacy:
        gym_in = to_gym_session_in(_legacy_to_session_in(record))
        if gym_in is None:
            continue
        user = await users_crud.get_by_id(session, record.user_id)
        migrated = await gym_crud.create_gym(
            session, record.user_id, gym_in, weight_kg=user.weight_kg if user else None
        )
        migrated.created_at = record.created_at
        await session.delete(record)
    await session.commit()
    return len(legacy)
