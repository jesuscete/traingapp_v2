import asyncio
import json
import logging

import httpx
import redis.asyncio as aioredis

from app.core.config import settings
from app.parsing.stub import parse_text

WORKOUT_PARSE_QUEUE = "workout:parse"

logger = logging.getLogger(__name__)


async def process_one(redis: aioredis.Redis) -> bool:
    item = await redis.brpop(WORKOUT_PARSE_QUEUE, timeout=1)
    if item is None:
        return False
    _, payload = item
    data = json.loads(payload)
    draft = parse_text(data["rawText"])
    body = {
        "userId": data["userId"],
        "session": draft.model_dump(mode="json"),
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.internal_api_url}/internal/sessions",
            json=body,
            headers={"X-Internal-Token": settings.internal_token},
        )
        response.raise_for_status()
    logger.info("Parsed request %s -> session %s", data["requestId"], response.json()["id"])
    return True


async def main() -> None:
    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    while True:
        try:
            await process_one(redis)
        except Exception:
            logger.exception("Worker error; continuing")
        await asyncio.sleep(0.1)


if __name__ == "__main__":
    asyncio.run(main())
