"""Recomendación por objetivo, determinista: objetivo -> cualidades -> patrones -> ejercicios.

Ordena los patrones por lo que te falta (análisis de deporte) y por la prioridad de la
cualidad; filtra por tu material y nivel; prescribe series/reps según el foco del objetivo.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog import normalize_exercise_name
from app.analytics.patterns import PATTERN_LABELS
from app.crud import catalog as catalog_crud
from app.models import User
from app.schemas.sport_analysis import RecommendationItemOut, RecommendationOut
from app.schemas.sport_profile import Goal
from app.services import exercise_engine, sport_analysis, sport_registry

MAX_ITEMS = 5


def _deficits(analysis_patterns: list[object]) -> dict[str, float]:
    """Proporción cubierta por patrón (0 = nada, 1 = objetivo cumplido)."""
    result: dict[str, float] = {}
    for status in analysis_patterns:
        key = getattr(status, "key", None)
        low = getattr(status, "low", 0) or 0
        value = getattr(status, "value", 0) or 0
        if isinstance(key, str) and low > 0:
            result[key] = min(1.0, value / low)
    return result


def _ordered_patterns(
    sport: str, goal: Goal, coverage: dict[str, float]
) -> tuple[list[str], dict[str, str], dict[str, str]]:
    """Patrones del objetivo en rondas: el principal de cada cualidad (por prioridad) primero,
    luego los secundarios. A igual rango, antes lo que menos cubres."""
    doc = sport_registry.profile_doc(sport)
    qualities = sorted(
        (q for q in doc.qualities if q.key in goal.qualities and q.patterns),
        key=lambda q: (-q.priority, goal.qualities.index(q.key)),
    )
    ranked: list[tuple[int, int, float, str]] = []
    quality_of: dict[str, str] = {}
    focus_of: dict[str, str] = {}
    for q_index, quality in enumerate(qualities):
        for depth, pattern in enumerate(quality.patterns):
            if pattern in quality_of:
                continue
            quality_of[pattern] = quality.label
            focus_of[pattern] = quality.focus or goal.focus
            ranked.append((depth, q_index, coverage.get(pattern, 0.0), pattern))
    ranked.sort()
    order = [p for *_, p in ranked]
    # Segunda ronda: otra opción solo para los patrones de la cualidad principal.
    top = [p for p in qualities[0].patterns] if qualities else []
    return order + [p for p in top if p in order], quality_of, focus_of


def _sport_name(user: User, doc: object) -> str:
    """Nombre del deporte tal como lo practica el usuario («running», no el perfil triatlón)."""
    for raw in [user.primary_sport, *(user.sports or [])]:
        if raw and sport_registry.resolve_sport(str(raw)) == getattr(doc, "sport", None):
            return str(raw)
    return str(getattr(doc, "label", "tu deporte")).lower()


def _default_goal(sport: str) -> Goal:
    doc = sport_registry.profile_doc(sport)
    top = sorted((q for q in doc.qualities if q.patterns), key=lambda q: -q.priority)[:3]
    return Goal(
        key="general",
        label=f"Preparación para {doc.label.lower()}",
        synonyms=["general"],
        qualities=[q.key for q in top] or [doc.qualities[0].key],
        focus=top[0].focus or "fuerza" if top else "fuerza",
    )


async def recommend(
    session: AsyncSession,
    user: User,
    *,
    text: str | None = None,
    goal_key: str | None = None,
    sport: str | None = None,
) -> RecommendationOut:
    sport_key = sport_analysis.main_sport(user, sport)
    doc = sport_registry.profile_doc(sport_key)
    goal = next((g for g in doc.goals if g.key == goal_key), None) if goal_key else None
    if goal is None and text:
        goal = sport_registry.find_goal(sport_key, text)
    resolved = goal is not None
    goal = goal or _default_goal(sport_key)

    rows = await catalog_crud.list_visible(session, user.id)
    catalog = [sport_analysis.catalog_item(r) for r in rows]
    analysis = await sport_analysis.analyze_user(
        session, user, sport=sport_key, weeks=4, basis="auto"
    )
    coverage = _deficits(list(analysis.patterns))
    sets_of = {
        str(getattr(t, "key", "")): (
            float(getattr(t, "value", 0) or 0),
            float(getattr(t, "low", 0) or 0),
        )
        for t in analysis.patterns
    }
    patterns, quality_of, focus_of = _ordered_patterns(sport_key, goal, coverage)
    allowed = exercise_engine.user_allowed_equipment(user)
    items: list[RecommendationItemOut] = []
    used: set[object] = set()
    used_names: set[str] = set()
    for pattern in patterns:
        picks = exercise_engine.pick_for_pattern(
            pattern,
            catalog,
            key_names=doc.key_exercises.get(pattern, []),
            allowed=allowed,
            exclude_ids=used,
            user_level=user.fitness_level,
            limit=1,
        )
        for item in picks:
            used.add(item.row.id)
            if normalize_exercise_name(item.name) in used_names:
                continue
            used_names.add(normalize_exercise_name(item.name))
            rx = exercise_engine.prescribe_for(item, pattern, focus_of[pattern], user.fitness_level)
            done, target = sets_of.get(pattern, (0.0, 0.0))
            gap = (
                f" · ahora no lo trabajas (objetivo: {target:g} series/semana)"
                if target and done == 0
                else f" · llevas {done:g} de {target:g} series/semana"
                if target and done < target
                else ""
            )
            items.append(
                RecommendationItemOut(
                    exercise_id=item.row.id,
                    name=item.name,
                    image_url=item.first_image,
                    equipment=item.equipment,
                    equipment_label=exercise_engine.equipment_label(item.equipment),
                    pattern=pattern,
                    pattern_label=PATTERN_LABELS[pattern],
                    quality=quality_of.get(pattern, ""),
                    reason=f"{PATTERN_LABELS[pattern]}: {quality_of.get(pattern, '')}{gap}",
                    sets=rx.sets,
                    reps_min=rx.reps_min,
                    reps_max=rx.reps_max,
                    rest_seconds=rx.rest_seconds,
                    note=rx.note,
                )
            )
        if len(items) >= MAX_ITEMS:
            break
    qualities = [q.label for q in doc.qualities if q.key in goal.qualities]
    where = "" if doc.sport == sport_registry.DEFAULT_SPORT else f" en {_sport_name(user, doc)}"
    summary = f"Para «{goal.label.lower()}»{where} cuentan: " + "; ".join(qualities) + "."
    if not resolved:
        summary = "No he reconocido un objetivo concreto, así que te propongo lo básico. " + summary
    return RecommendationOut(
        sport=doc.sport,
        sport_label=doc.label,
        goal_key=goal.key if resolved else None,
        goal_label=goal.label,
        focus=goal.focus,
        items=items[:MAX_ITEMS],
        summary=summary,
    )
