import json
import uuid
from datetime import UTC, datetime
from typing import Annotated, cast

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics.impacts import (
    compute_discipline_impacts,
    compute_muscle_impacts,
)
from app.api.deps import get_current_user
from app.chat.conversation import (
    append_live,
    close_live,
    get_live,
    is_end,
    is_routine_start,
    is_start,
    start_live,
    start_live_routine,
)
from app.chat.plan_session import (
    PlanResult,
    get_plan,
    plan_intent,
    process_plan_message,
)
from app.chat.plan_session import (
    cancel_plan as cancel_plan_session,
)
from app.chat.plan_session import (
    confirm_plan as confirm_plan_session,
)
from app.chat.routine_session import (
    build_routine_exercises,
    merge_draft_into_live,
    resolve_routine_day,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.parser import fetch_draft
from app.core.redis import get_redis
from app.crud import gym as gym_crud
from app.crud import routine as routine_crud
from app.crud import sessions
from app.crud.catalog import exercise_muscle_map
from app.crud.disciplines import load_catalog
from app.models import User
from app.schemas.chat import (
    ChatCancelIn,
    ChatConfirmIn,
    ChatEnqueueOut,
    ChatMessageIn,
    ChatMessageOut,
    ExerciseDraftOut,
    WorkoutDraftOut,
)
from app.schemas.gym import (
    GymSessionIn,
    GymSessionOut,
    MuscleImpactOut,
    SetEntryIn,
    WorkoutExerciseIn,
    WorkoutSetIn,
)
from app.schemas.plan import PlanDecisionIn
from app.schemas.session import (
    Discipline,
    ExerciseIn,
    SessionIn,
    SessionOut,
)
from app.schemas.session import (
    MuscleImpactOut as LegacyMuscleImpactOut,
)

WORKOUT_PARSE_QUEUE = "workout:parse"
DRAFT_PREFIX = "chat:draft"

router = APIRouter(prefix="/chat", tags=["chat"])


def _draft_key(user_id: uuid.UUID, request_id: uuid.UUID) -> str:
    return f"{DRAFT_PREFIX}:{user_id}:{request_id}"


@router.post(
    "/message",
    response_model=ChatEnqueueOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_message(
    body: ChatMessageIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatEnqueueOut:
    request_id = uuid.uuid4()
    payload = json.dumps(
        {
            "requestId": str(request_id),
            "userId": str(current_user.id),
            "rawText": body.text,
        }
    )
    await redis.lpush(WORKOUT_PARSE_QUEUE, payload)
    return ChatEnqueueOut(requestId=request_id, status="queued")


@router.post("/draft", response_model=ChatMessageOut)
async def create_draft(
    body: ChatMessageIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageOut:
    live = await get_live(redis, current_user.id)

    plan = await get_plan(redis, current_user.id)
    if plan is not None or (live is None and plan_intent(body.text) != "none"):
        result = await process_plan_message(redis, current_user.id, session, body.text)
        if result is not None:
            return _plan_message_out(result)

    if live is None and is_routine_start(body.text):
        routine = await routine_crud.get_active_routine(session, current_user.id)
        day = resolve_routine_day(routine, body.text) if routine is not None else None
        if day is not None:
            if day.day_type == "deporte":
                discipline_name = "other"
                if day.discipline_id is not None:
                    discipline = await routine_crud.get_discipline(
                        session, day.discipline_id
                    )
                    if discipline is not None:
                        discipline_name = discipline.normalized_name
                started = await start_live_routine(
                    redis,
                    current_user.id,
                    discipline=discipline_name,
                    routine_day_id=day.id,
                    exercises=[],
                )
            else:
                exercises = await build_routine_exercises(session, day)
                started = await start_live_routine(
                    redis,
                    current_user.id,
                    discipline="gym",
                    routine_day_id=day.id,
                    exercises=exercises,
                )
            return ChatMessageOut(
                mode="routine",
                liveSessionId=started.live_session_id,
                startedAt=started.started_at,
            )

    if live is None and is_start(body.text):
        started = await start_live(redis, current_user.id)
        return ChatMessageOut(
            mode="live",
            liveSessionId=started.live_session_id,
            startedAt=started.started_at,
        )
    if live is not None and is_end(body.text):
        if live.origin == "routine":
            return ChatMessageOut(
                mode="routine",
                liveSessionId=live.live_session_id,
                startedAt=live.started_at,
                entriesCount=len(live.entries),
            )
        closed = await close_live(redis, current_user.id)
        assert closed is not None
        combined = "; ".join(closed.entries)
        request_id = uuid.uuid4()
        payload = await fetch_draft(combined)
        draft = WorkoutDraftOut.model_validate(payload)
        duration = int((datetime.now(UTC) - closed.started_at).total_seconds() / 60)
        draft.performed_at = closed.started_at
        if duration > 0:
            draft.duration_minutes = duration
        await redis.setex(
            _draft_key(current_user.id, request_id),
            settings.chat_draft_ttl_seconds,
            draft.model_dump_json(),
        )
        return ChatMessageOut(
            mode="confirm",
            requestId=request_id,
            draft=draft,
            liveSessionId=closed.live_session_id,
            startedAt=closed.started_at,
            entriesCount=len(closed.entries),
        )
    if live is not None:
        if live.origin == "routine":
            payload = await fetch_draft(body.text)
            draft = WorkoutDraftOut.model_validate(payload)
            if draft.exercises:
                await merge_draft_into_live(
                    redis, current_user.id, draft.exercises, session
                )
            else:
                await append_live(redis, current_user.id, body.text)
            updated = await get_live(redis, current_user.id)
            assert updated is not None
            return ChatMessageOut(
                mode="routine",
                liveSessionId=updated.live_session_id,
                startedAt=updated.started_at,
                entriesCount=len(updated.entries),
            )
        updated = await append_live(redis, current_user.id, body.text)
        assert updated is not None
        return ChatMessageOut(
            mode="live",
            liveSessionId=updated.live_session_id,
            startedAt=updated.started_at,
            entriesCount=len(updated.entries),
        )
    request_id = uuid.uuid4()
    payload = await fetch_draft(body.text)
    draft = WorkoutDraftOut.model_validate(payload)
    await redis.setex(
        _draft_key(current_user.id, request_id),
        settings.chat_draft_ttl_seconds,
        draft.model_dump_json(),
    )
    return ChatMessageOut(mode="direct", requestId=request_id, draft=draft)


def _plan_message_out(result: PlanResult) -> ChatMessageOut:
    return ChatMessageOut(
        mode="plan",
        requestId=result.request_id,
        message=result.message,
        splits=result.splits,
        plan=result.plan,
        planStatus=result.status,
    )


def _to_exercise_in(exercise: ExerciseDraftOut) -> ExerciseIn:
    details = (
        {"perSetReps": exercise.per_set_reps}
        if exercise.per_set_reps is not None
        else None
    )
    return ExerciseIn(
        name=exercise.name,
        sets=exercise.sets,
        reps=exercise.reps,
        weight_kg=exercise.weight_kg,
        details=details,
    )


def _to_gym_session_in(
    draft: WorkoutDraftOut,
    body: ChatConfirmIn,
    exercises: list[ExerciseDraftOut],
    rpe: float | None,
    details: dict[str, object],
) -> GymSessionIn:
    workout_exercises: list[WorkoutExerciseIn] = []
    for i, ex in enumerate(exercises):
        if ex.per_set_reps:
            sets = [
                WorkoutSetIn(
                    set_number=j + 1,
                    set_type="normal",
                    entries=[SetEntryIn(entry_order=0, reps=reps, weight=ex.weight_kg)],
                )
                for j, reps in enumerate(ex.per_set_reps)
            ]
        elif ex.sets:
            sets = [
                WorkoutSetIn(
                    set_number=j + 1,
                    set_type="normal",
                    entries=[SetEntryIn(entry_order=0, reps=ex.reps, weight=ex.weight_kg)],
                )
                for j in range(ex.sets)
            ]
        else:
            sets = [
                WorkoutSetIn(
                    set_number=1,
                    set_type="normal",
                    entries=[
                        SetEntryIn(entry_order=0, reps=None, weight=ex.weight_kg)
                    ],
                )
            ]
        workout_exercises.append(
            WorkoutExerciseIn(name=ex.name, order_index=i, sets=sets)
        )
    return GymSessionIn(
        raw_text=draft.raw_text,
        performed_at=body.performedAt or draft.performed_at,
        duration_minutes=body.durationMinutes or draft.duration_minutes,
        intensity=int(rpe) if rpe is not None else None,
        fatigue=(
            int(body.perceivedFatigue) if body.perceivedFatigue is not None else None
        ),
        details=details or None,
        exercises=workout_exercises,
    )


@router.post(
    "/confirm",
    response_model=GymSessionOut | SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_draft(
    body: ChatConfirmIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    key = _draft_key(current_user.id, body.requestId)
    stored = await redis.get(key)
    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found or expired",
        )
    await redis.delete(key)
    draft = WorkoutDraftOut.model_validate_json(stored)
    exercises = body.exercises if body.exercises is not None else draft.exercises
    rpe = (
        body.suggestedRpe
        if body.suggestedRpe is not None
        else draft.suggested_rpe
    )
    details: dict[str, object] = {}
    if rpe is not None:
        details["rpe"] = rpe
    if body.perceivedFatigue is not None:
        details["perceivedFatigue"] = body.perceivedFatigue
    if body.workoutType is not None:
        details["workoutType"] = body.workoutType
    catalog = await exercise_muscle_map(session)

    if draft.discipline == "gym":
        gym_in = _to_gym_session_in(draft, body, exercises, rpe, details)
        record = await gym_crud.create_gym(
            session, current_user.id, gym_in, weight_kg=current_user.weight_kg
        )
        flat = gym_analytics.flatten_workout_exercises(record.workout_exercises)
        impacts = compute_muscle_impacts(flat, catalog)
        out_gym = GymSessionOut.model_validate(record)
        record_details = record.details or {}
        calories = record_details.get("calories")
        out_gym.calories = calories if isinstance(calories, (int, float)) else None
        out_gym.muscle_impacts = [
            MuscleImpactOut(
                muscle_group=item.muscle_group,
                activation=item.activation,
                zone=item.zone,
            )
            for item in impacts
        ]
        return out_gym

    session_in = SessionIn(
        discipline=cast(Discipline, draft.discipline),
        rawText=draft.raw_text,
        performedAt=body.performedAt or draft.performed_at,
        durationMinutes=body.durationMinutes or draft.duration_minutes,
        distanceMeters=body.distanceMeters,
        intensity=int(rpe) if rpe is not None else None,
        fatigue=(
            int(body.perceivedFatigue)
            if body.perceivedFatigue is not None
            else None
        ),
        details=details or None,
        exercises=[_to_exercise_in(exercise) for exercise in exercises],
    )
    record = await sessions.create(
        session, current_user.id, session_in, weight_kg=current_user.weight_kg
    )
    impacts = compute_muscle_impacts(record.exercises, catalog)
    if not impacts:
        discipline_info = (await load_catalog(session)).info(record.discipline)
        impacts = compute_discipline_impacts(
            record.discipline,
            profile=discipline_info.profile if discipline_info else None,
        )
    out_legacy = SessionOut.model_validate(record)
    out_legacy.muscle_impacts = [
        LegacyMuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
        for item in impacts
    ]
    return out_legacy


@router.post("/cancel")
async def cancel_draft(
    body: ChatCancelIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    await redis.delete(_draft_key(current_user.id, body.requestId))
    return {"status": "cancelled"}


@router.post(
    "/plan/confirm",
    response_model=ChatMessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_plan(
    body: PlanDecisionIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageOut:
    result = await confirm_plan_session(
        redis, current_user.id, session, body.planRequestId
    )
    return _plan_message_out(result)


@router.post("/plan/cancel", response_model=ChatMessageOut)
async def cancel_plan(
    body: PlanDecisionIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatMessageOut:
    result = await cancel_plan_session(redis, current_user.id, body.planRequestId)
    return _plan_message_out(result)
