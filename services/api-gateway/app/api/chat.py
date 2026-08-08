import json
import uuid
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.redis import get_redis
from app.models import User
from app.schemas.chat import ChatEnqueueOut, ChatMessageIn

WORKOUT_PARSE_QUEUE = "workout:parse"

router = APIRouter(prefix="/chat", tags=["chat"])


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
