"""Historial, récords y progresión de un ejercicio para un usuario."""

import uuid
from dataclasses import asdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics import records
from app.analytics.strength import estimated_1rm
from app.crud import catalog as catalog_crud
from app.models import WorkoutSet
from app.schemas.exercise_history import (
    ExerciseHistoryOut,
    ExerciseRecordsOut,
    HistorySessionOut,
    HistorySetOut,
    ProgressPointOut,
)


def _history_set(workout_set: WorkoutSet) -> HistorySetOut:
    entries = sorted(workout_set.entries, key=lambda e: e.entry_order)
    main = entries[0] if entries else None
    reps = main.reps if main else None
    weight = gym_analytics.normalize_weight(main.weight, main.weight_unit) if main else None
    return HistorySetOut(
        set_number=workout_set.set_number,
        set_type=workout_set.set_type,
        is_warmup=workout_set.is_warmup,
        reps=reps,
        weight_kg=weight,
        rpe=main.rpe if main else None,
        e1rm_kg=None
        if workout_set.is_warmup
        else estimated_1rm(weight, reps, main.rpe if main else None),
    )


async def build_history(
    session: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID, *, limit: int
) -> ExerciseHistoryOut:
    rows = await catalog_crud.exercise_history(session, user_id, exercise_id, limit=limit)
    sessions_out = [
        HistorySessionOut(
            session_id=ts.id,
            performed_at=ts.performed_at,
            sets=[_history_set(s) for s in sorted(we.sets, key=lambda s: s.set_number)],
        )
        for ts, we in rows
    ]
    performances = [
        records.SessionPerformance(
            session_id=str(item.session_id),
            performed_at=item.performed_at,
            sets=[
                records.SetPerformance(
                    reps=s.reps, weight_kg=s.weight_kg, is_warmup=s.is_warmup, rpe=s.rpe
                )
                for s in item.sets
            ],
        )
        for item in sessions_out
    ]
    progress = [records.progress_point(p) for p in reversed(performances)]
    return ExerciseHistoryOut(
        exercise_id=exercise_id,
        records=ExerciseRecordsOut(**asdict(records.compute_records(performances))),
        progress=[ProgressPointOut(**asdict(p)) for p in progress],
        sessions=sessions_out,
    )
