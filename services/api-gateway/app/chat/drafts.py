"""Almacenamiento de borradores de sesión (chat y agente) en Redis."""

import uuid

import redis.asyncio as aioredis

from app.core.config import settings
from app.schemas.chat import WorkoutDraftOut

DRAFT_PREFIX = "chat:draft"


def draft_key(user_id: uuid.UUID, request_id: uuid.UUID) -> str:
    return f"{DRAFT_PREFIX}:{user_id}:{request_id}"


async def save_draft(
    redis: aioredis.Redis, user_id: uuid.UUID, draft: WorkoutDraftOut
) -> uuid.UUID:
    """Guarda el borrador y devuelve su requestId (se confirma con /chat/confirm)."""
    request_id = uuid.uuid4()
    await redis.setex(
        draft_key(user_id, request_id), settings.chat_draft_ttl_seconds, draft.model_dump_json()
    )
    return request_id
