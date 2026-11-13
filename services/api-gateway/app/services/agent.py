"""Bucle del agente conversacional: memoria, pasos del LLM y ejecución de herramientas."""

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

import httpx
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import agent as agent_client
from app.crud import goals as goals_crud
from app.crud import routine as routine_crud
from app.models import User, UserGoal
from app.schemas.agent import AgentActionOut, AgentReplyOut
from app.schemas.nutrition import MealBatchIn
from app.services import nutrition, sport_analysis
from app.services.agent_tools import TOOLS, ToolArgumentError, ToolContext

logger = logging.getLogger(__name__)

MEMORY_PREFIX = "agent:conv"
MEMORY_TTL_SECONDS = 24 * 3600
MEMORY_MAX_MESSAGES = 30
CONTEXT_MESSAGES = 16
MAX_TOOL_STEPS = 4
MAX_TOOL_CONTENT = 12000
UNAVAILABLE = "El asistente no está disponible ahora mismo. Inténtalo en un rato."
SPORT_LABELS = {"boxing": "boxeo", "martial_arts": "artes marciales", "triathlon": "triatlón"}


def _key(user_id: uuid.UUID) -> str:
    return f"{MEMORY_PREFIX}:{user_id}"


async def load_history(redis: aioredis.Redis, user_id: uuid.UUID) -> list[dict[str, str]]:
    raw = await redis.get(_key(user_id))
    data = json.loads(raw) if raw else []
    return data if isinstance(data, list) else []


async def save_history(
    redis: aioredis.Redis, user_id: uuid.UUID, history: list[dict[str, str]]
) -> None:
    trimmed = history[-MEMORY_MAX_MESSAGES:]
    await redis.setex(_key(user_id), MEMORY_TTL_SECONDS, json.dumps(trimmed))


async def reset(redis: aioredis.Redis, user_id: uuid.UUID) -> None:
    await redis.delete(_key(user_id))


def _context(user: User, goals: list[UserGoal]) -> dict[str, object]:
    sport = sport_analysis.main_sport(user, None)
    today = datetime.now(UTC).date()
    return {
        "hoy": today.isoformat(),
        "usuario": user.name,
        "deporte_principal": SPORT_LABELS.get(sport, sport),
        "otros_deportes": user.sports or [],
        "peso_kg": user.weight_kg,
        "objetivo": user.goal,
        # Metas activas (la principal primero) para orientar planes y consejos.
        "metas": [
            {
                "titulo": g.title,
                "tipo": g.kind,
                "principal": g.is_primary,
                "fecha": g.target_date.isoformat() if g.target_date else None,
                "dias_restantes": (g.target_date - today).days if g.target_date else None,
            }
            for g in goals
            if not g.done
        ][:3],
    }


async def _run_tool(
    ctx: ToolContext, name: str, arguments: dict[str, object]
) -> tuple[str, AgentActionOut | None]:
    tool = TOOLS[name]
    try:
        result = await tool.handler(ctx, arguments)
    except ToolArgumentError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False), None
    except (httpx.HTTPError, ValueError):
        logger.exception("Agent tool %s failed", name)
        return json.dumps({"error": "No se pudo completar la herramienta"}), None
    content = json.dumps(result.content, ensure_ascii=False, default=str)
    if len(content) > MAX_TOOL_CONTENT:
        # Nunca truncar en silencio: el LLM interpretaria el JSON cortado como completo.
        content = (
            content[:MAX_TOOL_CONTENT]
            + " …[RESULTADO TRUNCADO: datos incompletos; pide un subconjunto más pequeño]"
        )
    return content, result.action


async def run_turn(
    session: AsyncSession, redis: aioredis.Redis, user: User, text: str
) -> AgentReplyOut:
    history = await load_history(redis, user.id)
    history.append({"role": "usuario", "content": text})
    ctx = ToolContext(session=session, redis=redis, user=user)
    actions: list[AgentActionOut] = []
    tools_used: list[str] = []
    specs = [t.spec() for t in TOOLS.values()]
    goals = await goals_crud.list_goals(session, user.id)

    reply = UNAVAILABLE
    source: Literal["llm", "fallback"] = "fallback"
    for step in range(MAX_TOOL_STEPS + 1):
        payload: dict[str, object] = {
            "context": _context(user, goals),
            "tools": specs,
            "messages": history[-CONTEXT_MESSAGES:],
            "forceAnswer": step == MAX_TOOL_STEPS,
        }
        try:
            decision = await agent_client.fetch_agent_step(payload)
        except (httpx.HTTPError, ValueError):
            logger.exception("Agent step request failed")
            break
        tool_name = decision.get("tool")
        if decision.get("action") != "herramienta" or tool_name not in TOOLS:
            reply = str(decision.get("message") or UNAVAILABLE)
            source = "llm" if decision.get("source") == "llm" else "fallback"
            break
        raw_args = decision.get("arguments")
        arguments = raw_args if isinstance(raw_args, dict) else {}
        content, action = await _run_tool(ctx, str(tool_name), arguments)
        tools_used.append(str(tool_name))
        if action is not None:
            actions.append(action)
        history.append({"role": "herramienta", "tool": str(tool_name), "content": content})

    history.append({"role": "asistente", "content": reply})
    await save_history(redis, user.id, history)
    return AgentReplyOut(source=source, reply=reply, actions=actions, tools_used=tools_used)


async def confirm_action(session: AsyncSession, user: User, action: dict[str, object]) -> str:
    """Ejecuta una propuesta del agente ya confirmada por el usuario."""
    if action["type"] == "save_meal":
        batch = MealBatchIn.model_validate(
            {"eaten_on": action["eaten_on"], "meal": action["meal"], "items": action["items"]}
        )
        await nutrition.add_batch(session, user.id, batch.eaten_on, batch.meal, batch.items, "ia")
        return f"Hecho: {action['summary']}."
    routine_id = uuid.UUID(str(action["routine_id"]))
    routine = await routine_crud.get_routine(session, user.id, routine_id)
    if routine is None:
        raise ToolArgumentError("La rutina ya no existe")
    exercise_id = uuid.UUID(str(action["exercise_id"]))
    if action["type"] == "swap_exercise":
        updated = await routine_crud.swap_exercise(
            session, routine, uuid.UUID(str(action["routine_exercise_id"])), exercise_id
        )
    elif action["type"] == "add_exercise":
        updated = await routine_crud.add_exercise(
            session,
            routine,
            int(str(action["day_of_week"])),
            exercise_id,
            sets=int(str(action["sets"])),
            reps_min=int(str(action["reps_min"])),
            reps_max=int(str(action["reps_max"])),
        )
    else:
        raise ToolArgumentError("Tipo de acción desconocido")
    if updated is None:
        raise ToolArgumentError("La rutina ha cambiado y la propuesta ya no aplica")
    return f"Hecho: {action['summary']}."
