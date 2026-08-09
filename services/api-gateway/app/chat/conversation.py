"""Estado transitorio de "sesion en vivo" (Redis) — Paso 1 Chat.

El usuario puede abrir una sesion ("empiezo entrenamiento"), ir anotando
series ("press banca 5x5 80kg") y cerrarla ("he terminado"). Todo el estado
vive en Redis (nunca en Postgres) con TTL de seguridad; al cerrar se genera
un borrador que pasa por el flujo de confirmacion habitual.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import redis.asyncio as aioredis

from app.core.config import settings

LIVE_SESSION_KEY = "live:session"

_START_PATTERNS: tuple[str, ...] = (
    r"empiezo (el |mi )?(entrenamiento|entreno|sesion|rutina|gimnasio)",
    r"comienzo (el |mi )?(entrenamiento|entreno|sesion|rutina|gimnasio)",
    r"inicio (el |mi )?(entrenamiento|entreno|sesion|rutina|gimnasio)",
    r"voy a (empezar|entrenar)",
    r"vamos a (empezar|entrenar)",
    r"empieza (el |mi )?entrenamiento",
    r"empezamos",
)

_END_PATTERNS: tuple[str, ...] = (
    r"he terminado",
    r"he acabado",
    r"termine (el |mi |la )?(entrenamiento|entreno|sesion|rutina)?",
    r"acabe (el |mi |la )?(entrenamiento|entreno|sesion|rutina)?",
    r"fin (del |de la |de mi )?(entrenamiento|entreno|sesion|rutina)",
    r"finalizo (el |mi |la )?(entrenamiento|entreno|sesion|rutina)?",
)


def is_start(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _START_PATTERNS)


def is_end(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _END_PATTERNS)


@dataclass
class LiveSession:
    live_session_id: uuid.UUID
    started_at: datetime
    entries: list[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))


def _key(user_id: uuid.UUID) -> str:
    return f"{LIVE_SESSION_KEY}:{user_id}"


def _dump(live: LiveSession) -> str:
    return json.dumps(
        {
            "liveSessionId": str(live.live_session_id),
            "startedAt": live.started_at.isoformat(),
            "entries": live.entries,
            "lastActivity": live.last_activity.isoformat(),
        }
    )


def _load(raw: str) -> LiveSession:
    data = json.loads(raw)
    return LiveSession(
        live_session_id=uuid.UUID(data["liveSessionId"]),
        started_at=datetime.fromisoformat(data["startedAt"]),
        entries=list(data["entries"]),
        last_activity=datetime.fromisoformat(data["lastActivity"]),
    )


async def get_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession | None:
    raw = await redis.get(_key(user_id))
    return _load(str(raw)) if raw is not None else None


async def start_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession:
    live = LiveSession(live_session_id=uuid.uuid4(), started_at=datetime.now(UTC))
    await redis.setex(_key(user_id), settings.live_session_ttl_seconds, _dump(live))
    return live


async def append_live(redis: aioredis.Redis, user_id: uuid.UUID, text: str) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None:
        return None
    live.entries.append(text)
    live.last_activity = datetime.now(UTC)
    await redis.setex(_key(user_id), settings.live_session_ttl_seconds, _dump(live))
    return live


async def close_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None:
        return None
    await redis.delete(_key(user_id))
    return live
