"""Sesion en curso (Redis) compartida por Chat y Seleccion manual.

Ambas pestanas leen y escriben el MISMO estado en Redis (`live:session`).
`/live/start` con `routineDayId` prellenan la sesion con los ejercicios y
series objetivo de la rutina (peso null + sugerido); sin `routineDayId` se
abre una sesion libre vacia. `/live/finish` persiste en las tablas de sesion
reales SOLO las series con peso relleno (serie sin peso = no hecha; ejercicio
sin ninguna serie con peso = no hecho), reutilizando los CRUD ya existentes.
"""

from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics.impacts import compute_discipline_impacts, compute_muscle_impacts
from app.api.deps import get_current_user
from app.chat.conversation import (
    LiveSession,
    LiveSet,
    add_live_exercise,
    add_live_set,
    close_live,
    get_live,
    start_live,
    start_live_routine,
    update_live_set,
)
from app.chat.routine_session import build_routine_exercises
from app.core.database import get_db
from app.core.redis import get_redis
from app.crud import gym as gym_crud
from app.crud import routine as routine_crud
from app.crud import sessions
from app.crud.catalog import exercise_muscle_map
from app.crud.disciplines import load_catalog
from app.models import User
from app.schemas.gym import (
    GymSessionIn,
    GymSessionOut,
    MuscleImpactOut,
    SetEntryIn,
    WorkoutExerciseIn,
    WorkoutSetIn,
)
from app.schemas.live import (
    LiveAddExerciseIn,
    LiveAddSetIn,
    LiveFinishIn,
    LiveSessionOut,
    LiveSetUpdateIn,
    LiveStartIn,
)
from app.schemas.session import (
    Discipline,
    SessionIn,
    SessionOut,
)
from app.schemas.session import (
    MuscleImpactOut as LegacyMuscleImpactOut,
)

router = APIRouter(prefix="/live", tags=["live"])


def _to_out(live: LiveSession) -> LiveSessionOut:
    out = LiveSessionOut.model_validate(live)
    out.entries_count = len(live.entries)
    return out


def _live_to_gym_in(
    live: LiveSession,
    body: LiveFinishIn,
    performed_at: datetime,
) -> GymSessionIn:
    workout_exercises: list[WorkoutExerciseIn] = []
    raw_parts: list[str] = []
    for index, exercise in enumerate(live.exercises):
        sets_in: list[WorkoutSetIn] = []
        for workout_set in sorted(exercise.sets, key=lambda item: item.set_number):
            if workout_set.weight is None and not body.keep_sets_without_weight:
                continue
            reps = workout_set.reps or workout_set.target_reps_min
            sets_in.append(
                WorkoutSetIn(
                    set_number=workout_set.set_number,
                    set_type=workout_set.set_type,
                    is_warmup=workout_set.is_warmup,
                    entries=[
                        SetEntryIn(
                            entry_order=0,
                            reps=reps,
                            weight=workout_set.weight,
                        )
                    ],
                )
            )
        if not sets_in:
            continue
        workout_exercises.append(
            WorkoutExerciseIn(
                exercise_id=exercise.exercise_id,
                name=exercise.name,
                order_index=index,
                sets=sets_in,
            )
        )
        raw_parts.append(
            f"{exercise.name} ({len(sets_in)} series)"
        )
    if not workout_exercises:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay series con peso relleno que guardar",
        )
    return GymSessionIn(
        raw_text="; ".join(raw_parts),
        performed_at=performed_at,
        duration_minutes=body.duration_minutes,
        intensity=body.intensity,
        fatigue=body.fatigue,
        note=body.note,
        routine_day_id=live.routine_day_id,
        exercises=workout_exercises,
    )


@router.get("", response_model=LiveSessionOut | None)
async def get_live_session(
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiveSessionOut | None:
    live = await get_live(redis, current_user.id)
    return _to_out(live) if live is not None else None


@router.post("/start", response_model=LiveSessionOut)
async def start_live_session(
    body: LiveStartIn,
    redis: Annotated[Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiveSessionOut:
    if body.routine_day_id is None:
        live = await start_live(redis, current_user.id)
        return _to_out(live)

    day = await routine_crud.get_day_for_user(
        session, current_user.id, body.routine_day_id
    )
    if day is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Routine day not found"
        )
    if day.day_type == "deporte":
        discipline_name = "other"
        if day.discipline_id is not None:
            discipline = await routine_crud.get_discipline(session, day.discipline_id)
            if discipline is not None:
                discipline_name = discipline.normalized_name
        live = await start_live_routine(
            redis,
            current_user.id,
            discipline=discipline_name,
            routine_day_id=day.id,
            exercises=[],
        )
        return _to_out(live)

    exercises = await build_routine_exercises(session, day)
    live = await start_live_routine(
        redis,
        current_user.id,
        discipline="gym",
        routine_day_id=day.id,
        exercises=exercises,
    )
    return _to_out(live)


@router.patch("/set", response_model=LiveSessionOut)
async def update_set(
    body: LiveSetUpdateIn,
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiveSessionOut:
    live = await update_live_set(
        redis,
        current_user.id,
        exercise_index=body.exercise_index,
        set_number=body.set_number,
        weight=body.weight,
        reps=body.reps,
    )
    if live is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Live session or set not found"
        )
    return _to_out(live)


@router.post("/exercises", response_model=LiveSessionOut)
async def add_exercise(
    body: LiveAddExerciseIn,
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiveSessionOut:
    live = await add_live_exercise(
        redis,
        current_user.id,
        name=body.name,
        exercise_id=body.exercise_id,
        sets=[
            LiveSet(
                set_number=item.set_number,
                weight=item.weight,
                reps=item.reps,
            )
            for item in body.sets
        ],
    )
    if live is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Live session not found"
        )
    return _to_out(live)


@router.post("/exercises/{exercise_index}/sets", response_model=LiveSessionOut)
async def add_set(
    exercise_index: int,
    body: LiveAddSetIn,
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LiveSessionOut:
    live = await add_live_set(
        redis,
        current_user.id,
        exercise_index=exercise_index,
        set_number=body.set_number,
        weight=body.weight,
        reps=body.reps,
    )
    if live is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Live session not found"
        )
    return _to_out(live)


@router.post(
    "/finish",
    response_model=GymSessionOut | SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def finish_live_session(
    body: LiveFinishIn,
    redis: Annotated[Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    live = await get_live(redis, current_user.id)
    if live is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No live session"
        )
    performed_at = body.performed_at or live.started_at

    if live.discipline == "gym":
        gym_in = _live_to_gym_in(live, body, performed_at)
        record = await gym_crud.create_gym(
            session, current_user.id, gym_in, weight_kg=current_user.weight_kg
        )
        await close_live(redis, current_user.id)
        catalog = await exercise_muscle_map(session)
        flat = gym_analytics.flatten_workout_exercises(record.workout_exercises)
        impacts = compute_muscle_impacts(flat, catalog)
        out = GymSessionOut.model_validate(record)
        calories = (record.details or {}).get("calories")
        out.calories = calories if isinstance(calories, (int, float)) else None
        out.muscle_impacts = [
            MuscleImpactOut(
                muscle_group=item.muscle_group,
                activation=item.activation,
                zone=item.zone,
            )
            for item in impacts
        ]
        return out

    if live.discipline is not None and live.discipline != "gym":
        session_in = SessionIn(
            discipline=cast(Discipline, live.discipline),
            raw_text=f"Sesion de {live.discipline}",
            performed_at=performed_at,
            duration_minutes=body.duration_minutes,
            intensity=body.intensity,
            fatigue=body.fatigue,
            note=body.note,
            routine_day_id=live.routine_day_id,
            exercises=[],
        )
        record = await sessions.create(
            session, current_user.id, session_in, weight_kg=current_user.weight_kg
        )
        await close_live(redis, current_user.id)
        catalog = await exercise_muscle_map(session)
        impacts = compute_muscle_impacts(record.exercises, catalog)
        if not impacts:
            discipline_info = (await load_catalog(session)).info(record.discipline)
            impacts = compute_discipline_impacts(
                record.discipline,
                profile=discipline_info.profile if discipline_info else None,
            )
        out_sport = SessionOut.model_validate(record)
        out_sport.muscle_impacts = [
            LegacyMuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
            for item in impacts
        ]
        return out_sport

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="La sesion en curso no tiene disciplina asignada",
    )


@router.delete("")
async def cancel_live_session(
    redis: Annotated[Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    await close_live(redis, current_user.id)
    return {"status": "cancelled"}
