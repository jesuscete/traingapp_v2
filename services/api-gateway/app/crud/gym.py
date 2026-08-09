import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import gym as gym_analytics
from app.analytics import kcal as kcal_analytics
from app.analytics.catalog import normalize_exercise_name
from app.crud.catalog import catalog_lookup, uses_bodyweight_map
from app.models import (
    SetEntry,
    TrainingSession,
    WorkoutExercise,
    WorkoutSessionSummary,
    WorkoutSet,
)
from app.schemas.gym import GymSessionIn

_LOADS = (
    selectinload(TrainingSession.workout_exercises)
    .selectinload(WorkoutExercise.sets)
    .selectinload(WorkoutSet.entries),
    selectinload(TrainingSession.summary),
)


def _duration_min(data: GymSessionIn) -> int:
    if data.duration_minutes is not None:
        return data.duration_minutes
    if data.start_time is not None and data.end_time is not None:
        return max(0, int((data.end_time - data.start_time).total_seconds() / 60))
    return 0


def _build_kcal_input(data: GymSessionIn) -> tuple[kcal_analytics.ExerciseInput, ...]:
    inputs: list[kcal_analytics.ExerciseInput] = []
    for ex in data.exercises:
        working_sets = [ws for ws in ex.sets if not ws.is_warmup]
        reps_by_set = [
            sum(e.reps for e in ws.entries if e.reps is not None)
            for ws in working_sets
        ]
        weights: list[float] = []
        for ws in working_sets:
            for e in ws.entries:
                normalized = gym_analytics.normalize_weight(e.weight, e.weight_unit)
                if normalized is not None:
                    weights.append(normalized)
        rest = next(
            (ws.rest_seconds for ws in working_sets if ws.rest_seconds is not None),
            None,
        )
        inputs.append(
            kcal_analytics.ExerciseInput(
                name=ex.name,
                weight_kg=max(weights) if weights else None,
                sets=len(working_sets),
                reps=max(reps_by_set) if reps_by_set else None,
                per_set_reps=reps_by_set or None,
                rest_seconds=rest,
            )
        )
    return tuple(inputs)


async def create_gym(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: GymSessionIn,
    *,
    weight_kg: float | None = None,
) -> TrainingSession:
    lookup = await catalog_lookup(session)
    bw_map = await uses_bodyweight_map(session)

    summary_result = gym_analytics.compute_summary(
        data.exercises, user_weight_kg=weight_kg, uses_bodyweight_map=bw_map
    )

    details = dict(data.details or {})
    if data.calories is not None:
        details["calories"] = data.calories
    estimate = kcal_analytics.estimate(
        kcal_analytics.SessionKcalInput(
            discipline="gym",
            weight_kg=weight_kg,
            duration_minutes=data.duration_minutes,
            rpe=data.intensity,
            exercises=_build_kcal_input(data),
        )
    )
    details["kcal_confidence"] = estimate.confidence
    details["kcal_confidence_level"] = estimate.confidence_level
    details["kcal_factors"] = estimate.factors

    record = TrainingSession(
        user_id=user_id,
        discipline="gym",
        raw_text=data.raw_text,
        performed_at=data.performed_at,
        start_time=data.start_time,
        end_time=data.end_time,
        intensity=data.intensity,
        fatigue=data.fatigue,
        duration_minutes=data.duration_minutes,
        note=data.note,
        details=details or None,
        estimated_kcal=estimate.kcal,
        volume_kg=summary_result.total_volume,
    )
    session.add(record)
    await session.flush()

    workout_exercises: list[WorkoutExercise] = []
    for i, exercise in enumerate(data.exercises):
        cat = lookup.get(normalize_exercise_name(exercise.name))
        uses_bw = bool(cat and cat.uses_bodyweight)
        volume = gym_analytics.compute_exercise_volume(
            exercise, user_weight_kg=weight_kg, uses_bodyweight=uses_bw
        )
        we = WorkoutExercise(
            session_id=record.id,
            exercise_id=getattr(cat, "id", None) if cat else None,
            name=exercise.name,
            order_index=exercise.order_index or i,
            superset_group_id=exercise.superset_group_id,
            volume_kg=volume.volume_kg,
        )
        for ws_in, ws_volume in zip(exercise.sets, volume.set_volumes):
            ws = WorkoutSet(
                set_number=ws_in.set_number,
                set_type=ws_in.set_type,
                rest_seconds=None if ws_in.set_type == "dropset" else ws_in.rest_seconds,
                is_warmup=ws_in.is_warmup,
                volume_kg=ws_volume,
            )
            for entry in sorted(ws_in.entries, key=lambda e: e.entry_order):
                ws.entries.append(
                    SetEntry(
                        entry_order=entry.entry_order,
                        reps=entry.reps,
                        weight=gym_analytics.normalize_weight(entry.weight, entry.weight_unit),
                        weight_unit=entry.weight_unit,
                        duration_seconds=entry.duration_seconds,
                        distance_meters=entry.distance_meters,
                        rpe=entry.rpe,
                        side=entry.side,
                    )
                )
            we.sets.append(ws)
        workout_exercises.append(we)

    session.add_all(workout_exercises)
    session.add(
        WorkoutSessionSummary(
            session_id=record.id,
            total_volume=summary_result.total_volume,
            avg_rpe=summary_result.avg_rpe,
            sets_count=summary_result.sets_count,
            duration_min=_duration_min(data),
        )
    )
    await session.commit()

    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == record.id)
        .options(*_LOADS)
    )
    return result.scalar_one()


async def get_gym_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> TrainingSession | None:
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == session_id, TrainingSession.user_id == user_id)
        .options(*_LOADS)
    )
    return result.scalar_one_or_none()


async def list_gym_by_user(
    session: AsyncSession, user_id: uuid.UUID, *, limit: int = 20, offset: int = 0
) -> list[TrainingSession]:
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.user_id == user_id, TrainingSession.discipline == "gym")
        .options(*_LOADS)
        .order_by(TrainingSession.performed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
