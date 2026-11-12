"""Límite de intentos con Redis (login y registro): contador con caducidad por clave."""

import redis.asyncio as aioredis

PREFIX = "ratelimit"


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            f"Demasiados intentos. Prueba de nuevo en {max(1, retry_after // 60)} min."
        )
        self.retry_after = retry_after


async def check(redis: aioredis.Redis, key: str, limit: int) -> None:
    """Lanza `RateLimited` si la clave ya alcanzó el límite en la ventana actual."""
    count = await redis.get(f"{PREFIX}:{key}")
    if count is not None and int(count) >= limit:
        ttl = await redis.ttl(f"{PREFIX}:{key}")
        raise RateLimited(ttl if ttl and ttl > 0 else 60)


async def hit(redis: aioredis.Redis, key: str, window_seconds: int) -> int:
    name = f"{PREFIX}:{key}"
    count = int(await redis.incr(name))
    if count == 1:
        await redis.expire(name, window_seconds)
    return count


async def reset(redis: aioredis.Redis, key: str) -> None:
    await redis.delete(f"{PREFIX}:{key}")
