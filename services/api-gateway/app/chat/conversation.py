"""Estado transitorio de "sesion en vivo" (Redis) — Chat + Seleccion manual.

El usuario puede abrir una sesion ("empiezo entrenamiento"), ir anotando
series ("press banca 5x5 80kg") y cerrarla ("he terminado"). Todo el estado
vive en Redis (nunca en Postgres) con TTL de seguridad.

Cuando el usuario registra un dia de rutina, la sesion se inicializa
PREPOBLADA con los ejercicios/series objetivo de ese dia (peso null +
sugerido) y queda en la MISMA key de Redis para que la pestana de chat y la
de seleccion manual lean/escriban el mismo estado:

    live:session:{user_id} -> LiveSession (con `exercises` estructurado)

Los campos `entries` se conservan para el flujo libre por texto; el flujo de
rutina usa `exercises` (peso/reps por serie). `origin` distingue
"free" (texto libre) de "routine" (prepoblado desde plantilla).
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import cast

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

# Deteccion de "he hecho el entrenamiento de hoy" (registro desde rutina).
_ROUTINE_START_PATTERNS: tuple[str, ...] = (
    r"he hecho (el |mi |la )?(entrenamiento|entreno|sesion|rutina|dia)",
    r"hice (el |mi |la )?(entrenamiento|entreno|sesion|rutina|dia)",
    r"he realizado (el |mi |la )?(entrenamiento|entreno|sesion|rutina|dia)",
    r"registra (el |mi |la )?(entrenamiento|entreno|sesion|rutina) de hoy",
    r"he hecho (el |mi )?entrenamiento de hoy",
    r"hoy (he |hice )(entrenado|entrenamiento|entreno|sesion|rutina)",
)

_TODAY_PATTERN = re.compile(r"\b(?:de hoy|hoy)\b", re.IGNORECASE)
_DAY_LABEL_PATTERN = re.compile(
    r"(?:dia|día) (?:de )?(?:empuje|traccion|pierna|piernas|push|pull|legs|tren "
    r"superior|tren inferior|superior|inferior|gluteo|gluteos|brazos|espalda|pecho|"
    r"full body|cuerpo completo)",
    re.IGNORECASE,
)

_DAY_OF_WEEK: dict[str, int] = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 3,
    "thursday": 4,
    "friday": 5,
    "saturday": 6,
    "sunday": 7,
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
    "domingo": 7,
}
_WEEKDAY_PATTERN = re.compile(
    r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo|monday|tuesday|"
    r"wednesday|thursday|friday|saturday|sunday)\b",
    re.IGNORECASE,
)


def is_start(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _START_PATTERNS)


def is_end(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _END_PATTERNS)


def is_routine_start(text: str) -> bool:
    return any(
        re.search(pattern, text, re.IGNORECASE) for pattern in _ROUTINE_START_PATTERNS
    )


def is_today(text: str) -> bool:
    return _TODAY_PATTERN.search(text) is not None


def extract_day_hint(text: str) -> str | None:
    """Etiqueta del dia mencionada ("he hecho el dia de piernas" -> "piernas")."""
    match = _DAY_LABEL_PATTERN.search(text)
    if match is None:
        return None
    parts = match.group(0).lower().split(" ")
    return parts[-1] if parts else None


def extract_weekday(text: str) -> int | None:
    """Dia de la semana (1-7) mencionado explicitamente, si lo hay."""
    match = _WEEKDAY_PATTERN.search(text)
    if match is None:
        return None
    return _DAY_OF_WEEK[match.group(1).lower()]


@dataclass
class LiveSet:
    set_number: int
    set_type: str = "normal"
    target_reps_min: int | None = None
    target_reps_max: int | None = None
    reps: int | None = None
    weight: float | None = None
    suggested_weight: float | None = None
    is_warmup: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "setNumber": self.set_number,
            "setType": self.set_type,
            "targetRepsMin": self.target_reps_min,
            "targetRepsMax": self.target_reps_max,
            "reps": self.reps,
            "weight": self.weight,
            "suggestedWeight": self.suggested_weight,
            "isWarmup": self.is_warmup,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LiveSet":
        return cls(
            set_number=int(cast(int, data["setNumber"])),
            set_type=str(data.get("setType", "normal")),
            target_reps_min=_opt_int(data.get("targetRepsMin")),
            target_reps_max=_opt_int(data.get("targetRepsMax")),
            reps=_opt_int(data.get("reps")),
            weight=_opt_float(data.get("weight")),
            suggested_weight=_opt_float(data.get("suggestedWeight")),
            is_warmup=bool(data.get("isWarmup", False)),
        )


@dataclass
class LiveExercise:
    name: str
    exercise_id: uuid.UUID | None = None
    order_index: int = 0
    routine_exercise_id: uuid.UUID | None = None
    sets: list[LiveSet] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "exerciseId": str(self.exercise_id) if self.exercise_id else None,
            "orderIndex": self.order_index,
            "routineExerciseId": (
                str(self.routine_exercise_id) if self.routine_exercise_id else None
            ),
            "sets": [item.to_dict() for item in self.sets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "LiveExercise":
        exercise_id = data.get("exerciseId")
        routine_exercise_id = data.get("routineExerciseId")
        raw_sets = data.get("sets")
        sets_data = raw_sets if isinstance(raw_sets, list) else []
        return cls(
            name=str(data["name"]),
            exercise_id=(
                uuid.UUID(exercise_id) if isinstance(exercise_id, str) else None
            ),
            order_index=_opt_int(data.get("orderIndex")) or 0,
            routine_exercise_id=(
                uuid.UUID(routine_exercise_id)
                if isinstance(routine_exercise_id, str)
                else None
            ),
            sets=[
                LiveSet.from_dict(cast(dict[str, object], item)) for item in sets_data
            ],
        )


@dataclass
class LiveSession:
    live_session_id: uuid.UUID
    started_at: datetime
    entries: list[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=lambda: datetime.now(UTC))
    origin: str = "free"  # "free" | "routine"
    discipline: str | None = None
    routine_day_id: uuid.UUID | None = None
    exercises: list[LiveExercise] = field(default_factory=list)


def _opt_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        return int(value)
    return None


def _opt_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    return None


def _key(user_id: uuid.UUID) -> str:
    return f"{LIVE_SESSION_KEY}:{user_id}"


def _dump(live: LiveSession) -> str:
    return json.dumps(
        {
            "liveSessionId": str(live.live_session_id),
            "startedAt": live.started_at.isoformat(),
            "entries": live.entries,
            "lastActivity": live.last_activity.isoformat(),
            "origin": live.origin,
            "discipline": live.discipline,
            "routineDayId": (
                str(live.routine_day_id) if live.routine_day_id else None
            ),
            "exercises": [exercise.to_dict() for exercise in live.exercises],
        }
    )


def _load(raw: str) -> LiveSession:
    data = json.loads(raw)
    routine_day_id = data.get("routineDayId")
    return LiveSession(
        live_session_id=uuid.UUID(data["liveSessionId"]),
        started_at=datetime.fromisoformat(data["startedAt"]),
        entries=list(data.get("entries", [])),
        last_activity=datetime.fromisoformat(data["lastActivity"]),
        origin=str(data.get("origin", "free")),
        discipline=data.get("discipline"),
        routine_day_id=uuid.UUID(routine_day_id) if routine_day_id else None,
        exercises=[
            LiveExercise.from_dict(item) for item in data.get("exercises", []) or []
        ],
    )


async def _persist(
    redis: aioredis.Redis, user_id: uuid.UUID, live: LiveSession
) -> None:
    live.last_activity = datetime.now(UTC)
    await redis.setex(_key(user_id), settings.live_session_ttl_seconds, _dump(live))


async def get_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession | None:
    raw = await redis.get(_key(user_id))
    return _load(str(raw)) if raw is not None else None


async def start_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession:
    live = LiveSession(live_session_id=uuid.uuid4(), started_at=datetime.now(UTC))
    await _persist(redis, user_id, live)
    return live


async def start_live_routine(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    *,
    discipline: str,
    routine_day_id: uuid.UUID,
    exercises: list[LiveExercise],
) -> LiveSession:
    live = LiveSession(
        live_session_id=uuid.uuid4(),
        started_at=datetime.now(UTC),
        origin="routine",
        discipline=discipline,
        routine_day_id=routine_day_id,
        exercises=exercises,
    )
    await _persist(redis, user_id, live)
    return live


async def append_live(
    redis: aioredis.Redis, user_id: uuid.UUID, text: str
) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None:
        return None
    live.entries.append(text)
    await _persist(redis, user_id, live)
    return live


async def update_live_set(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    *,
    exercise_index: int,
    set_number: int,
    weight: float | None = None,
    reps: int | None = None,
) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None or not (0 <= exercise_index < len(live.exercises)):
        return None
    exercise = live.exercises[exercise_index]
    for workout_set in exercise.sets:
        if workout_set.set_number == set_number:
            if weight is not None:
                workout_set.weight = weight
            if reps is not None:
                workout_set.reps = reps
            await _persist(redis, user_id, live)
            return live
    return None


async def add_live_exercise(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    *,
    name: str,
    exercise_id: uuid.UUID | None = None,
    sets: list[LiveSet],
) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None:
        return None
    live.exercises.append(
        LiveExercise(
            name=name,
            exercise_id=exercise_id,
            order_index=len(live.exercises),
            sets=sets,
        )
    )
    await _persist(redis, user_id, live)
    return live


async def add_live_set(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    *,
    exercise_index: int,
    set_number: int,
    weight: float | None = None,
    reps: int | None = None,
) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None or not (0 <= exercise_index < len(live.exercises)):
        return None
    exercise = live.exercises[exercise_index]
    exercise.sets.append(LiveSet(set_number=set_number, weight=weight, reps=reps))
    await _persist(redis, user_id, live)
    return live


async def close_live(redis: aioredis.Redis, user_id: uuid.UUID) -> LiveSession | None:
    live = await get_live(redis, user_id)
    if live is None:
        return None
    await redis.delete(_key(user_id))
    return live


async def persist_live(
    redis: aioredis.Redis, user_id: uuid.UUID, live: LiveSession
) -> None:
    await _persist(redis, user_id, live)
