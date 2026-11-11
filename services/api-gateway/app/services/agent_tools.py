"""Herramientas del agente conversacional (M4).

Las de lectura devuelven datos del usuario en JSON compacto para el LLM. Las de escritura
nunca ejecutan: crean una acción pendiente que el usuario confirma desde la UI.
"""

import json
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import fatigue as fatigue_analytics
from app.analytics.catalog import normalize_exercise_name
from app.chat.drafts import save_draft
from app.core.parser import fetch_draft
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.crud import stats as stats_crud
from app.models import Routine, User
from app.schemas.agent import AgentActionOut
from app.schemas.chat import WorkoutDraftOut
from app.services import fatigue_engine, fatigue_input, sport_analysis

ACTION_PREFIX = "agent:action"
ACTION_TTL_SECONDS = 3600
MAX_RESULTS = 8
DAY_NAMES = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo",
}


class ToolArgumentError(ValueError):
    """Argumentos ausentes o inválidos: se devuelven al LLM para que corrija."""


@dataclass
class ToolContext:
    session: AsyncSession
    redis: aioredis.Redis
    user: User


@dataclass
class ToolResult:
    content: object
    action: AgentActionOut | None = None


Handler = Callable[[ToolContext, dict[str, object]], Awaitable[ToolResult]]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    handler: Handler
    parameters: dict[str, str] = field(default_factory=dict)
    writes: bool = False

    def spec(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "writes": self.writes,
        }


def _uuid_arg(args: dict[str, object], key: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(args.get(key)))
    except ValueError as exc:
        raise ToolArgumentError(f"'{key}' debe ser un id válido") from exc


def _int_arg(args: dict[str, object], key: str, default: int, low: int, high: int) -> int:
    value = args.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ToolArgumentError(f"'{key}' debe ser un número")
    try:
        number = int(value)
    except ValueError as exc:
        raise ToolArgumentError(f"'{key}' debe ser un número") from exc
    if not low <= number <= high:
        raise ToolArgumentError(f"'{key}' debe estar entre {low} y {high}")
    return number


def _str_arg(args: dict[str, object], key: str) -> str:
    value = args.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ToolArgumentError(f"Falta '{key}'")
    return value.strip()


# --- Lectura -----------------------------------------------------------------------------


async def _get_fatigue(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    states, _, _, _, today = await fatigue_engine.simulate_fatigue(ctx.session, ctx.user.id)
    current = states.get(today, {})
    ranked = sorted(current.items(), key=lambda kv: kv[1], reverse=True)
    return ToolResult(
        {
            "fecha": today.isoformat(),
            "escala": "0-100 (70 aviso, 85 peligro)",
            "musculos": [
                {"grupo": g, "fatiga": round(v, 1), "nivel": fatigue_analytics.fatigue_level(v)}
                for g, v in ranked
            ],
        }
    )


async def _explain_fatigue(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    group = _str_arg(args, "grupo")
    if group not in fatigue_analytics.MUSCLE_GROUPS:
        raise ToolArgumentError(f"Grupo desconocido; usa uno de {fatigue_analytics.MUSCLE_GROUPS}")
    inp = await fatigue_engine.fatigue_inputs(ctx.session, ctx.user.id, 28)
    parts = fatigue_analytics.contributions(
        inp.events,
        inp.readiness,
        inp.weights,
        inp.today,
        group,
        doms_by_group=inp.doms,
        tau2_factors=inp.tau2_factors,
    )
    return ToolResult(
        {
            "grupo": group,
            "fatiga": round(sum(p.remaining for p in parts), 1),
            "sesiones": [
                {
                    "fecha": p.performed_on.isoformat(),
                    "deporte": p.session.discipline,
                    "descripcion": (p.session.label or "")[:60],
                    "queda": p.remaining,
                }
                for p in parts[:5]
            ],
        }
    )


async def _recent_sessions(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    days = _int_arg(args, "dias", 14, 1, 90)
    records = await stats_crud.sessions_in_range(
        ctx.session, ctx.user.id, datetime.now(UTC) - timedelta(days=days)
    )
    return ToolResult(
        {
            "dias": days,
            "sesiones": [
                {
                    "fecha": ts.performed_at.date().isoformat(),
                    "deporte": ts.discipline,
                    "descripcion": ts.raw_text[:60],
                    "minutos": ts.duration_minutes,
                    "rpe": fatigue_input.session_rpe(ts),
                    "volumen_kg": round(ts.volume_kg),
                }
                for ts in records[-15:]
            ],
        }
    )


async def _sport_analysis(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    result = await sport_analysis.analyze_user(
        ctx.session, ctx.user, sport=None, weeks=4, basis="auto"
    )
    return ToolResult(
        {
            "deporte": result.label,
            "base": result.basis,
            "puntuacion": result.score,
            "carencias": [
                {
                    "mensaje": g.message,
                    "gravedad": g.severity,
                    "sugerencias": [
                        {"exercise_id": str(s.exercise_id), "nombre": s.name} for s in g.suggestions
                    ],
                }
                for g in result.gaps[:6]
            ],
        }
    )


def _routine_summary(routine: Routine, names: dict[uuid.UUID, str]) -> dict[str, object]:
    return {
        "routine_id": str(routine.id),
        "nombre": routine.name,
        "dias": [
            {
                "dia": d.day_of_week,
                "nombre_dia": DAY_NAMES[d.day_of_week],
                "tipo": d.day_type,
                "ejercicios": [
                    {
                        "routine_exercise_id": str(e.id),
                        "exercise_id": str(e.exercise_id),
                        "nombre": names.get(e.exercise_id, "?"),
                        "series": len(e.sets),
                        "reps": f"{e.sets[0].target_reps_min}-{e.sets[0].target_reps_max}"
                        if e.sets
                        else None,
                    }
                    for e in d.exercises
                ],
            }
            for d in sorted(routine.days, key=lambda d: d.day_of_week)
        ],
    }


async def _names(ctx: ToolContext) -> dict[uuid.UUID, str]:
    rows = await catalog_crud.list_visible(ctx.session, ctx.user.id)
    out: dict[uuid.UUID, str] = {}
    for row in rows:
        details = row.details or {}
        name_es = details.get("nameEs")
        out[row.id] = name_es if isinstance(name_es, str) and name_es else row.name
    return out


async def _get_routine(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    routine = await routine_crud.get_active_routine(ctx.session, ctx.user.id)
    if routine is None:
        return ToolResult({"rutina": None, "nota": "El usuario no tiene rutina activa."})
    return ToolResult(_routine_summary(routine, await _names(ctx)))


async def _search_exercises(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    query = normalize_exercise_name(_str_arg(args, "texto"))
    names = await _names(ctx)
    rows = await catalog_crud.list_visible(ctx.session, ctx.user.id)
    hits = [
        {"exercise_id": str(r.id), "nombre": names[r.id]}
        for r in rows
        if query in r.normalized_name or query in normalize_exercise_name(names[r.id])
    ]
    return ToolResult({"resultados": hits[:MAX_RESULTS]})


async def _alternatives(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    exercise_id = _uuid_arg(args, "exercise_id")
    result = await sport_analysis.alternatives(ctx.session, ctx.user, exercise_id, limit=5)
    if result is None:
        raise ToolArgumentError("Ejercicio no encontrado")
    return ToolResult(
        {
            "alternativas": [
                {"exercise_id": str(a.exercise_id), "nombre": a.name, "similitud": a.similarity}
                for a in result
            ]
        }
    )


# --- Escritura (solo propuestas) ---------------------------------------------------------


async def _store_action(ctx: ToolContext, payload: dict[str, object]) -> str:
    action_id = str(uuid.uuid4())
    await ctx.redis.setex(
        f"{ACTION_PREFIX}:{ctx.user.id}:{action_id}", ACTION_TTL_SECONDS, json.dumps(payload)
    )
    return action_id


async def load_action(
    redis: aioredis.Redis, user_id: uuid.UUID, action_id: str
) -> dict[str, object] | None:
    raw = await redis.get(f"{ACTION_PREFIX}:{user_id}:{action_id}")
    if raw is None:
        return None
    data = json.loads(raw)
    return data if isinstance(data, dict) else None


async def drop_action(redis: aioredis.Redis, user_id: uuid.UUID, action_id: str) -> None:
    await redis.delete(f"{ACTION_PREFIX}:{user_id}:{action_id}")


async def _log_workout(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    text = _str_arg(args, "texto")
    draft = WorkoutDraftOut.model_validate(await fetch_draft(text))
    request_id = await save_draft(ctx.redis, ctx.user.id, draft)
    summary = f"Registrar {draft.discipline}"
    if draft.duration_minutes:
        summary += f" · {draft.duration_minutes} min"
    if draft.exercises:
        summary += f" · {len(draft.exercises)} ejercicios"
    action = AgentActionOut(
        id=str(request_id), type="save_workout", summary=summary, request_id=request_id
    )
    return ToolResult(
        {"propuesta": summary, "borrador": draft.model_dump(mode="json", by_alias=True)},
        action,
    )


async def _active_routine(ctx: ToolContext) -> Routine:
    routine = await routine_crud.get_active_routine(ctx.session, ctx.user.id)
    if routine is None:
        raise ToolArgumentError("El usuario no tiene rutina activa")
    return routine


async def _visible(ctx: ToolContext, exercise_id: uuid.UUID) -> None:
    if await catalog_crud.invisible_ids(ctx.session, ctx.user.id, {exercise_id}):
        raise ToolArgumentError("Ejercicio no encontrado en el catálogo")


async def _swap_exercise(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    entry_id = _uuid_arg(args, "routine_exercise_id")
    exercise_id = _uuid_arg(args, "exercise_id")
    routine = await _active_routine(ctx)
    await _visible(ctx, exercise_id)
    entry = next((e for d in routine.days for e in d.exercises if e.id == entry_id), None)
    if entry is None:
        raise ToolArgumentError("Ese ejercicio no está en la rutina activa")
    names = await _names(ctx)
    day = next(d for d in routine.days if entry in d.exercises)
    summary = (
        f"Cambiar {names.get(entry.exercise_id, '?')} por {names.get(exercise_id, '?')} "
        f"({DAY_NAMES[day.day_of_week]})"
    )
    action_id = await _store_action(
        ctx,
        {
            "type": "swap_exercise",
            "routine_id": str(routine.id),
            "routine_exercise_id": str(entry_id),
            "exercise_id": str(exercise_id),
            "summary": summary,
        },
    )
    return ToolResult(
        {"propuesta": summary}, AgentActionOut(id=action_id, type="swap_exercise", summary=summary)
    )


async def _add_exercise(ctx: ToolContext, args: dict[str, object]) -> ToolResult:
    day = _int_arg(args, "dia", 1, 1, 7)
    exercise_id = _uuid_arg(args, "exercise_id")
    sets = _int_arg(args, "series", 3, 1, 10)
    reps_min = _int_arg(args, "reps_min", 8, 1, 50)
    reps_max = _int_arg(args, "reps_max", max(reps_min, 12), reps_min, 50)
    routine = await _active_routine(ctx)
    await _visible(ctx, exercise_id)
    target = next((d for d in routine.days if d.day_of_week == day), None)
    if target is None or target.day_type != "gimnasio":
        raise ToolArgumentError(f"El {DAY_NAMES[day]} no es día de gimnasio en la rutina")
    names = await _names(ctx)
    summary = (
        f"Añadir {names.get(exercise_id, '?')} {sets}×{reps_min}-{reps_max} el {DAY_NAMES[day]}"
    )
    action_id = await _store_action(
        ctx,
        {
            "type": "add_exercise",
            "routine_id": str(routine.id),
            "day_of_week": day,
            "exercise_id": str(exercise_id),
            "sets": sets,
            "reps_min": reps_min,
            "reps_max": reps_max,
            "summary": summary,
        },
    )
    return ToolResult(
        {"propuesta": summary}, AgentActionOut(id=action_id, type="add_exercise", summary=summary)
    )


TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        Tool("ver_fatiga", "Fatiga muscular actual por grupo (0-100).", _get_fatigue),
        Tool(
            "explicar_fatiga",
            "Qué sesiones cargan un grupo muscular y cuánto queda de cada una.",
            _explain_fatigue,
            {
                "grupo": "quadriceps|hamstrings|glutes|calves|core|back|chest|"
                "shoulders|biceps|triceps|forearms|neck"
            },
        ),
        Tool(
            "sesiones_recientes",
            "Entrenos de los últimos días.",
            _recent_sessions,
            {"dias": "número de días (por defecto 14)"},
        ),
        Tool(
            "analisis_deporte",
            "Análisis de la preparación para el deporte principal: puntuación, "
            "carencias y ejercicios sugeridos (con exercise_id).",
            _sport_analysis,
        ),
        Tool(
            "ver_rutina",
            "Rutina activa con días, ejercicios, routine_exercise_id y exercise_id.",
            _get_routine,
        ),
        Tool(
            "buscar_ejercicios",
            "Busca ejercicios del catálogo por nombre.",
            _search_exercises,
            {"texto": "parte del nombre"},
        ),
        Tool(
            "alternativas_ejercicio",
            "Ejercicios parecidos para sustituir uno.",
            _alternatives,
            {"exercise_id": "id del ejercicio"},
        ),
        Tool(
            "registrar_entreno",
            "Prepara el registro de un entreno descrito en lenguaje natural.",
            _log_workout,
            {"texto": "descripción del entreno tal como la da el usuario"},
            writes=True,
        ),
        Tool(
            "sustituir_en_rutina",
            "Propone cambiar un ejercicio de la rutina activa por otro.",
            _swap_exercise,
            {
                "routine_exercise_id": "id de la entrada en la rutina",
                "exercise_id": "id del ejercicio nuevo",
            },
            writes=True,
        ),
        Tool(
            "anadir_a_rutina",
            "Propone añadir un ejercicio a un día de gimnasio de la rutina.",
            _add_exercise,
            {
                "dia": "1=lunes … 7=domingo",
                "exercise_id": "id del ejercicio",
                "series": "por defecto 3",
                "reps_min": "por defecto 8",
                "reps_max": "por defecto 12",
            },
            writes=True,
        ),
    )
}
