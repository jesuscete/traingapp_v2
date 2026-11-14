"""Router determinista del chat (M10): un único punto que decide quién atiende cada mensaje.

Orden (precisión antes que cobertura; si duda, el mensaje sigue al agente con IA):
    1. flujo guiado activo o arranque claro (plan, entreno en vivo) -> handoff "guided"
    2. consultas de datos (rutina, qué toca, fatiga, comidas de hoy) -> tarjeta, sin IA
    3. «no tengo X» / alternativas a un ejercicio -> motor de alternativas, sin IA
    4. «mejorar mi pegada» (objetivo del perfil del deporte) -> recomendador, sin IA
    5. lo demás -> None (lo atiende el agente)
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog import normalize_exercise_name
from app.analytics.exercise_tags import EQUIPMENT_LABELS
from app.chat import cards
from app.chat.conversation import extract_weekday, get_live, is_routine_start, is_start
from app.chat.plan_session import get_plan, plan_intent
from app.core.config import settings
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.models import User
from app.schemas.agent import AgentReplyOut, ChatCardOut
from app.services import recommendations, sport_analysis, sport_registry
from app.services.sport_analysis import CatalogItem

LAST_EXERCISES_KEY = "chat:last_exercises"
LAST_EXERCISES_TTL = 2 * 3600
ALTERNATIVES_PER_EXERCISE = 4
MIN_EXERCISE_NAME = 5

# Material en lenguaje natural -> código del catálogo (más largo primero).
EQUIPMENT_WORDS: tuple[tuple[str, str], ...] = (
    ("balon medicinal", "medicine ball"),
    ("balones medicinales", "medicine ball"),
    ("barra z", "e-z curl bar"),
    ("pesa rusa", "kettlebells"),
    ("kettlebell", "kettlebells"),
    ("mancuerna", "dumbbell"),
    ("polea", "cable"),
    ("maquina", "machine"),
    ("banda", "bands"),
    ("goma", "bands"),
    ("fitball", "exercise ball"),
    ("barra", "barbell"),
    ("balon", "medicine ball"),
)

_EDIT_WORDS = re.compile(
    r"\b(crea\w*|haz(me)?|cambia\w*|sustitu\w*|anad\w*|quita\w*|borra\w*|modifica\w*|"
    r"analiza\w*|revisa\w*|nueva|nuevo|por que|porque|explica\w*)\b"
)
# Pedir cambios o análisis de lo que ya existe no es «crear un plan».
_MODIFY = re.compile(
    r"\b(cambia\w*|sustitu\w*|anad\w*|quita\w*|borra\w*|modifica\w*|analiza\w*|revisa\w*|"
    r"dura|duro|por que|porque)\b"
)
_CONDITIONS = re.compile(
    r"\b(sparring|partido|competicion|competir|combate|torneo|carrera de|prueba|antes de|"
    r"despues de|vispera|lesion\w*|me duele|dolor)\b"
)
_WEEKDAY_WORDS = re.compile(r"\b(lunes|martes|miercoles|jueves|viernes|sabado|domingo)\b")
_ROUTINE = re.compile(r"\b(rutina|plan semanal|mi plan|mi semana)\b")
_SHOW = re.compile(
    r"\b(ver|ensena\w*|muestra\w*|cual es|que tengo|como es|dime|pasame|recuerdame|tengo)\b"
)
_WHAT_TODAY = re.compile(r"\bque (tengo|me toca|toca|hago|entreno)\b")
_WHEN = re.compile(r"\b(hoy|manana)\b")
_FATIGUE = re.compile(
    r"\b(fatiga\w*|cansancio|recuperad\w*|"
    r"como (voy|estoy|ando) de (fatiga|cansancio|recuperacion))\b"
)
_NUTRITION = re.compile(
    r"\b((que|cuanto) (he comido|llevo( comido)?)|calorias|macros|cuanta proteina|"
    r"como voy de (comida|calorias|proteina))\b"
)
_MISSING = re.compile(r"\b(no tengo|sin|me falta\w*|no hay|no dispongo de)\b")
_ALTERNATIVE = re.compile(
    r"\b(alternativa\w*|en vez de|en lugar de|otro ejercicio|que hago en (vez|lugar)|"
    r"parecido a|similar a)\b"
)
_IMPROVE = re.compile(
    r"\b(mejorar|mejore|ganar|aumentar|potenciar|trabajar|desarrollar|ejercicios para|"
    r"quiero|como puedo|ayudame a)\b"
)
_ROUTINE_WRITE = re.compile(r"\b(en mi rutina|de mi rutina|a mi rutina|por (el|la|un|una))\b")


@dataclass
class Route:
    intent: str  # guided | routine | fatigue | nutrition | alternatives | recommend | agent
    weekday: int | None = None
    missing_equipment: list[str] = field(default_factory=list)


def _enabled(node: str) -> bool:
    return node in {n.strip() for n in settings.chat_rule_nodes.split(",") if n.strip()}


def missing_equipment(normalized: str) -> list[str]:
    found: list[str] = []
    rest = f" {normalized} "
    for words, code in EQUIPMENT_WORDS:
        if f" {words}" in rest and code not in found:
            found.append(code)
            rest = rest.replace(f" {words}", " ")
    return found


def classify(text: str, *, today: int | None = None) -> Route:
    """Clasificación pura del texto (sin estado). `today`: 1-7 para «hoy/mañana»."""
    normalized = normalize_exercise_name(text)
    wants_plan = plan_intent(text) == "clear" and not _MODIFY.search(normalized)
    if wants_plan or is_start(normalized) or is_routine_start(normalized):
        return Route("guided")
    weekday = extract_weekday(normalized)
    when = _WHEN.search(normalized)
    if weekday is None and when and today is not None:
        weekday = today if when.group(1) == "hoy" else today % 7 + 1
    editing = _EDIT_WORDS.search(normalized) is not None
    # Preguntas con condiciones («tengo sparring el sábado, ¿qué hago el jueves?») o con varios
    # días necesitan razonar: no son una consulta de datos.
    conditional = (
        _CONDITIONS.search(normalized) is not None
        or len(_WEEKDAY_WORDS.findall(normalized)) > 1
    )
    if not editing and not conditional:
        if _ROUTINE.search(normalized) and (_SHOW.search(normalized) or len(normalized) < 20):
            return Route("routine", weekday=weekday)
        if _WHAT_TODAY.search(normalized) and weekday is not None:
            return Route("routine", weekday=weekday)
        if _FATIGUE.search(normalized):
            return Route("fatigue")
        if _NUTRITION.search(normalized) and not re.search(
            r"\b(apunta|registra|he comido un)", normalized
        ):
            return Route("nutrition")
    missing = missing_equipment(normalized) if _MISSING.search(normalized) else []
    if (missing or _ALTERNATIVE.search(normalized)) and not _ROUTINE_WRITE.search(normalized):
        if not re.search(r"\b(sustitu\w*|cambia\w*)\b", normalized):
            return Route("alternatives", missing_equipment=missing)
    if _IMPROVE.search(normalized) and not editing:
        return Route("recommend")
    return Route("agent")


async def _remember_exercises(
    redis: aioredis.Redis, user_id: uuid.UUID, exercise_ids: list[uuid.UUID]
) -> None:
    if exercise_ids:
        await redis.setex(
            f"{LAST_EXERCISES_KEY}:{user_id}",
            LAST_EXERCISES_TTL,
            json.dumps([str(i) for i in exercise_ids]),
        )


async def _last_exercises(redis: aioredis.Redis, user_id: uuid.UUID) -> list[uuid.UUID]:
    raw = await redis.get(f"{LAST_EXERCISES_KEY}:{user_id}")
    try:
        return [uuid.UUID(v) for v in json.loads(raw)] if raw else []
    except (ValueError, TypeError):
        return []


def find_exercise(normalized: str, catalog: list[CatalogItem]) -> CatalogItem | None:
    """Ejercicio del catálogo nombrado en el texto (la coincidencia más larga)."""
    best: tuple[int, CatalogItem] | None = None
    padded = f" {normalized} "
    for item in catalog:
        for name in {normalize_exercise_name(item.name), item.row.normalized_name}:
            if len(name) >= MIN_EXERCISE_NAME and f" {name} " in padded:
                if best is None or len(name) > best[0]:
                    best = (len(name), item)
    return best[1] if best else None


async def _alternatives(
    session: AsyncSession, redis: aioredis.Redis, user: User, text: str, route: Route
) -> tuple[ChatCardOut, str] | None:
    rows = await catalog_crud.list_visible(session, user.id)
    catalog = [sport_analysis.catalog_item(r) for r in rows]
    by_id = {c.row.id: c for c in catalog}
    normalized = normalize_exercise_name(text)
    named = find_exercise(normalized, catalog)
    sources: list[CatalogItem]
    if named is not None:
        sources = [named]
    else:
        recent = [by_id[i] for i in await _last_exercises(redis, user.id) if i in by_id]
        routine = await routine_crud.get_active_routine(session, user.id)
        in_routine = [
            by_id[ex.exercise_id]
            for day in (routine.days if routine else [])
            for ex in day.exercises
            if ex.exercise_id in by_id
        ]
        pool = recent + [c for c in in_routine if c not in recent]
        sources = [c for c in pool if c.equipment in route.missing_equipment]
    if not sources:
        return None
    groups = []
    for source in sources[:3]:
        alternatives = await sport_analysis.alternatives(
            session,
            user,
            source.row.id,
            limit=ALTERNATIVES_PER_EXERCISE,
            exclude_equipment=route.missing_equipment,
        )
        missing = (
            EQUIPMENT_LABELS.get(source.equipment)
            if source.equipment in route.missing_equipment
            else None
        )
        groups.append((source.name, missing, alternatives or []))
    await _remember_exercises(
        redis, user.id, [a.exercise_id for _, _, alts in groups for a in alts]
    )
    return cards.alternatives_card(groups)


async def handle(
    session: AsyncSession, redis: aioredis.Redis, user: User, text: str
) -> AgentReplyOut | None:
    """Respuesta sin IA si el mensaje encaja en un nodo determinista; si no, None."""
    if await get_plan(redis, user.id) is not None or await get_live(redis, user.id) is not None:
        return (
            AgentReplyOut(source="rules", reply="", handoff="guided")
            if _enabled("guided")
            else None
        )
    route = classify(text, today=datetime.now(UTC).isoweekday())
    if route.intent == "agent" or not _enabled(route.intent):
        return None
    if route.intent == "guided":
        return AgentReplyOut(source="rules", reply="", handoff="guided")

    card: ChatCardOut | None
    if route.intent == "routine":
        card, reply = await cards.routine_card(session, user, route.weekday)
    elif route.intent == "fatigue":
        card, reply = await cards.fatigue_card(session, user)
    elif route.intent == "nutrition":
        card, reply = await cards.nutrition_card(session, user)
    elif route.intent == "alternatives":
        result = await _alternatives(session, redis, user, text, route)
        if result is None:
            return None  # sin ejercicio claro: que lo resuelva el agente
        card, reply = result
    else:  # recommend
        sport = _sport_in_text(text) or sport_analysis.main_sport(user, None)
        if sport_registry.find_goal(sport, text) is None:
            return None
        rec = await recommendations.recommend(session, user, text=text, sport=sport)
        if not rec.items:
            return None
        card, reply = cards.recommendation_card(rec)
        await _remember_exercises(redis, user.id, [i.exercise_id for i in rec.items])

    await _append_history(redis, user.id, text, reply, card)
    return AgentReplyOut(
        source="rules",
        reply=reply,
        cards=[card] if card is not None else [],
        tools_used=[route.intent],
    )


def _sport_in_text(text: str) -> str | None:
    words = normalize_exercise_name(text).split()
    for size in (2, 1):
        for i in range(len(words) - size + 1):
            sport = sport_registry.resolve_sport(" ".join(words[i : i + size]))
            if sport:
                return sport
    return None


async def _append_history(
    redis: aioredis.Redis, user_id: uuid.UUID, text: str, reply: str, card: ChatCardOut | None
) -> None:
    """La conversación del agente recuerda lo respondido sin IA (para preguntas de seguimiento)."""
    from app.services import agent

    summary = reply
    if card is not None:
        names = [i.title for s in card.sections for i in s.items][:12]
        summary += f" [Tarjeta «{card.title}»: {', '.join(names)}]"
    history = await agent.load_history(redis, user_id)
    history.append({"role": "usuario", "content": text})
    history.append({"role": "asistente", "content": summary})
    await agent.save_history(redis, user_id, history)

