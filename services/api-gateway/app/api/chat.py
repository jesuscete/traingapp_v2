import json
import uuid
from typing import Annotated, cast

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.parser import fetch_draft
from app.core.redis import get_redis
from app.crud import sessions
from app.models import TrainingSession, User
from app.schemas.chat import (
    ChatCancelIn,
    ChatConfirmIn,
    ChatDraftOut,
    ChatEnqueueOut,
    ChatMessageIn,
    ExerciseDraftOut,
    WorkoutDraftOut,
)
from app.schemas.session import Discipline, ExerciseIn, SessionIn, SessionOut

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


@router.post("/draft", response_model=ChatDraftOut)
async def create_draft(
    body: ChatMessageIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatDraftOut:
    request_id = uuid.uuid4()
    payload = await fetch_draft(body.text)
    draft = WorkoutDraftOut.model_validate(payload)
    await redis.setex(
        _draft_key(current_user.id, request_id),
        settings.chat_draft_ttl_seconds,
        draft.model_dump_json(),
    )
    return ChatDraftOut(requestId=request_id, draft=draft)


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


@router.post(
    "/confirm",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_draft(
    body: ChatConfirmIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TrainingSession:
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
    details = {"rpe": rpe} if rpe is not None else None
    session_in = SessionIn(
        discipline=cast(Discipline, draft.discipline),
        rawText=draft.raw_text,
        performedAt=body.performedAt or draft.performed_at,
        durationMinutes=body.durationMinutes or draft.duration_minutes,
        details=details,
        exercises=[_to_exercise_in(exercise) for exercise in exercises],
    )
    return await sessions.create(
        session, current_user.id, session_in, weight_kg=current_user.weight_kg
    )


@router.post("/cancel")
async def cancel_draft(
    body: ChatCancelIn,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    await redis.delete(_draft_key(current_user.id, body.requestId))
    return {"status": "cancelled"}
