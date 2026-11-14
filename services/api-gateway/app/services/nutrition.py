"""Lógica de nutrición (M5): alimentos (caché + propios), comidas, objetivos, peso y platos."""

import logging
import re
import uuid
from collections import defaultdict
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta

import httpx
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement

from app.analytics import nutrition as calc
from app.core import food_sources
from app.core.config import settings
from app.models import (
    BodyWeightLog,
    Food,
    FoodAlias,
    MealEntry,
    MealTemplate,
    NutritionGoal,
    TrainingSession,
    User,
)
from app.schemas.nutrition import (
    EXACT_METHODS,
    DayOut,
    FoodFacetsOut,
    FoodIn,
    FoodOut,
    GoalIn,
    GoalOut,
    Meal,
    MealEntryIn,
    MealEntryOut,
    MealEntryUpdate,
    Method,
    ParseMealOut,
    ProposedItem,
    TargetOut,
    TemplateIn,
    TemplateItem,
    TemplateOut,
    Totals,
    WeekDayOut,
    WeekOut,
    WeightOut,
    WeightPointOut,
)
from app.services import meal_dictionary

logger = logging.getLogger(__name__)

MEALS = ("desayuno", "media_manana", "comida", "merienda", "cena", "dia")
LOCAL_RESULTS_ENOUGH = 8
_SEARCH_STOPWORDS = frozenset({"de", "del", "la", "el", "los", "las", "y", "con", "en", "al"})
_ACCENTS = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}


def _fold(text: str) -> str:
    text = text.lower()
    for accented, plain in _ACCENTS.items():
        text = text.replace(accented, plain)
    return text


def _folded(column: ColumnElement[str] | InstrumentedAttribute[str]) -> ColumnElement[str]:
    """lower() sin tildes en SQL (replace encadenados: vale en PostgreSQL y SQLite)."""
    expr: ColumnElement[str] = func.lower(column)
    for accented, plain in _ACCENTS.items():
        expr = func.replace(expr, accented, plain)
    return expr


_STEM_LENGTH = 6


_BRAND_SEPARATORS = (" ", "-", ".", "'", "&")


def _compact(text: str) -> str:
    """Clave de marca: sin tildes, mayúsculas ni separadores ("Alpen Fest" == "alpenfest")."""
    text = _fold(text)
    for sep in _BRAND_SEPARATORS:
        text = text.replace(sep, "")
    return text


def _compacted(column: ColumnElement[str]) -> ColumnElement[str]:
    expr = _folded(column)
    for sep in _BRAND_SEPARATORS:
        expr = func.replace(expr, sep, "")
    return expr


def search_terms(query: str) -> list[str]:
    """Patrones LIKE por palabra, sin tildes ni plurales: "cereales" -> "%cereal%"."""
    terms: list[str] = []
    for word in re.findall(r"\w+", _fold(query)):
        if len(word) < 2 or word in _SEARCH_STOPWORDS:
            continue
        if len(word) > 4 and word.endswith("es"):
            word = word[:-2]
        elif len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        # Raiz aproximada: "proteinas" -> "protei" casa con "protein"/"proteina".
        terms.append(f"%{word[:_STEM_LENGTH]}%")
    return terms


class NutritionError(ValueError):
    """Petición válida en forma pero imposible (alimento ajeno, ración inexistente...)."""


def food_out(food: Food, user_id: uuid.UUID | None = None) -> FoodOut:
    out = FoodOut.model_validate(food)
    out.is_custom = food.owner_user_id is not None and food.owner_user_id == user_id
    return out


# --- Alimentos ---------------------------------------------------------------------------


async def _cache(session: AsyncSession, cand: food_sources.FoodCandidate) -> Food:
    existing = await session.scalar(
        select(Food).where(Food.source == cand.source, Food.external_id == cand.external_id)
    )
    if existing is not None:
        return existing
    food = Food(
        source=cand.source,
        external_id=cand.external_id,
        barcode=cand.barcode,
        name=cand.name,
        brand=cand.brand,
        store=cand.store,
        kcal_100g=cand.kcal_100g,
        protein_100g=cand.protein_100g,
        carbs_100g=cand.carbs_100g,
        fat_100g=cand.fat_100g,
        fiber_100g=cand.fiber_100g,
        sugar_100g=cand.sugar_100g,
        servings=cand.servings,
    )
    session.add(food)
    await session.flush()
    return food


def _visible(user_id: uuid.UUID) -> ColumnElement[bool]:
    return or_(Food.owner_user_id.is_(None), Food.owner_user_id == user_id)


async def visible_food(session: AsyncSession, user_id: uuid.UUID, food_id: uuid.UUID) -> Food:
    food = await session.scalar(select(Food).where(Food.id == food_id, _visible(user_id)))
    if food is None:
        raise NutritionError("Alimento no encontrado")
    return food


async def search_foods(
    session: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    limit: int = 20,
    store: str | None = None,
    brand: str | None = None,
) -> list[FoodOut]:
    """Primero lo tuyo (usados recientemente y propios), luego la caché y por último OFF.

    `store` y `brand` filtran por supermercado y marca exactos (sin mayúsculas/tildes);
    con alguno puesto la consulta de texto puede ir vacía.
    """
    terms = search_terms(query) if query.strip() else []
    name, brand_col = _folded(Food.name), _folded(func.coalesce(Food.brand, ""))
    conditions: list[ColumnElement[bool]] = [
        or_(name.like(term), brand_col.like(term)) for term in terms
    ]
    if query.strip() and not terms:
        conditions.append(name.like(f"%{_fold(query.strip())}%"))
    if store:
        conditions.append(_folded(func.coalesce(Food.store, "")) == _fold(store.strip()))
    if brand:
        conditions.append(_compacted(func.coalesce(Food.brand, "")) == _compact(brand))
    matches = and_(*conditions)
    filtered = bool(store or brand)
    recent_ids = select(MealEntry.food_id).where(
        MealEntry.user_id == user_id, MealEntry.food_id.is_not(None)
    )
    local = list(
        (
            await session.scalars(
                select(Food)
                .where(_visible(user_id), matches)
                .order_by(
                    Food.owner_user_id.is_(None),  # propios primero
                    Food.id.not_in(recent_ids),  # luego los ya usados
                    Food.store.is_(None),  # luego los de supermercado importado (Lidl...)
                    func.length(Food.name),
                )
                .limit(limit)
            )
        ).all()
    )
    results = list(local)
    if settings.off_remote_search and not filtered and len(local) < LOCAL_RESULTS_ENOUGH:
        try:
            for cand in await food_sources.off_search(query, limit=12):
                results.append(await _cache(session, cand))
            await session.commit()
        except food_sources.FoodSourceError:
            logger.warning("Open Food Facts no disponible; solo resultados locales")
    seen: set[uuid.UUID] = set()
    unique: list[Food] = []
    for food in results:
        if food.id not in seen:
            seen.add(food.id)
            unique.append(food)
    return [food_out(f, user_id) for f in unique[:limit]]


async def food_facets(
    session: AsyncSession, user_id: uuid.UUID, store: str | None = None, limit: int = 300
) -> FoodFacetsOut:
    """Supermercados y marcas disponibles para filtrar (marcas del súper si se indica)."""
    stores = await session.scalars(
        select(Food.store)
        .where(_visible(user_id), Food.store.is_not(None))
        .group_by(Food.store)
        .order_by(func.count().desc())
    )
    brand_query = select(Food.brand).where(_visible(user_id), Food.brand.is_not(None))
    if store:
        brand_query = brand_query.where(
            _folded(func.coalesce(Food.store, "")) == _fold(store.strip())
        )
    brands = await session.scalars(
        brand_query.group_by(Food.brand).order_by(func.count().desc()).limit(limit)
    )
    # Varias grafías de la misma marca ("Alpen Fest"/"Alpenfest"): una sola opción, la más usada.
    unique: dict[str, str] = {}
    for value in brands:
        if value and value.strip():
            unique.setdefault(_compact(value), value.strip())
    return FoodFacetsOut(
        stores=[s for s in stores if s],
        brands=sorted(unique.values(), key=_fold),
    )


async def food_by_barcode(
    session: AsyncSession, user_id: uuid.UUID, barcode: str
) -> FoodOut | None:
    cached = await session.scalar(
        select(Food)
        .where(Food.barcode == barcode, _visible(user_id))
        .order_by(Food.owner_user_id.is_(None))
    )
    if cached is not None:
        return food_out(cached, user_id)
    cand = await food_sources.off_by_barcode(barcode)
    if cand is None:
        return None
    food = await _cache(session, cand)
    await session.commit()
    return food_out(food, user_id)


async def create_custom_food(session: AsyncSession, user_id: uuid.UUID, data: FoodIn) -> FoodOut:
    food = Food(
        owner_user_id=user_id,
        source="custom",
        external_id=None,
        **data.model_dump(exclude={"servings"}),
        servings=[s.model_dump() for s in data.servings],
    )
    session.add(food)
    await session.commit()
    return food_out(food, user_id)


# --- Comidas -----------------------------------------------------------------------------


def _from_food(food: Food, grams: float) -> dict[str, float | None]:
    return {
        "kcal": calc.scale_per_100g(food.kcal_100g, grams) or 0.0,
        "protein_g": calc.scale_per_100g(food.protein_100g, grams) or 0.0,
        "carbs_g": calc.scale_per_100g(food.carbs_100g, grams) or 0.0,
        "fat_g": calc.scale_per_100g(food.fat_100g, grams) or 0.0,
        "fiber_g": calc.scale_per_100g(food.fiber_100g, grams),
    }


def _serving_grams(food: Food, label: str | None) -> float:
    servings = food.servings or []
    chosen = next((s for s in servings if s.get("label") == label), None) if label else None
    chosen = chosen or (servings[0] if servings else None)
    grams = chosen.get("grams") if chosen else None
    if not isinstance(grams, (int, float)) or grams <= 0:
        raise NutritionError("Este alimento no tiene raciones: indica los gramos")
    return float(grams)


async def add_entry(session: AsyncSession, user_id: uuid.UUID, data: MealEntryIn) -> MealEntryOut:
    if data.food_id is not None:
        food = await visible_food(session, user_id, data.food_id)
        if data.grams is not None:
            grams, method = (
                data.grams,
                data.method or ("etiqueta" if food.source == "custom" else "pesada"),
            )
        else:
            grams = _serving_grams(food, data.serving_label) * (data.servings or 1)
            method = data.method or "racion"
        values = _from_food(food, grams)
        entry = MealEntry(
            user_id=user_id,
            eaten_on=data.eaten_on,
            meal=data.meal,
            food_id=food.id,
            name=food.name,
            grams=round(grams, 1),
            method=method,
            note=data.note,
            **values,
        )
    else:
        entry = MealEntry(
            user_id=user_id,
            eaten_on=data.eaten_on,
            meal=data.meal,
            food_id=None,
            name=data.name or "Añadido rápido",
            grams=None,
            kcal=data.kcal or 0.0,
            protein_g=data.protein_g or 0.0,
            carbs_g=data.carbs_g or 0.0,
            fat_g=data.fat_g or 0.0,
            fiber_g=None,
            method=data.method or "rapida",
            note=data.note,
        )
    session.add(entry)
    await session.commit()
    return MealEntryOut.model_validate(entry)


async def add_batch(
    session: AsyncSession,
    user_id: uuid.UUID,
    eaten_on: date,
    meal: Meal,
    items: list[ProposedItem],
    method: Method,
) -> list[MealEntryOut]:
    """Guarda una propuesta confirmada (texto libre): crea el alimento si hace falta."""
    created: list[MealEntry] = []
    for item in items:
        food = await visible_food(session, user_id, item.food_id) if item.food_id else None
        if food is None:
            food = Food(
                owner_user_id=user_id,
                source=item.source if item.source != "off" else "ia",
                name=item.name,
                kcal_100g=item.kcal_100g,
                protein_100g=item.protein_100g,
                carbs_100g=item.carbs_100g,
                fat_100g=item.fat_100g,
                fiber_100g=item.fiber_100g,
                servings=[],
            )
            session.add(food)
            await session.flush()
        entry = MealEntry(
            user_id=user_id,
            eaten_on=eaten_on,
            meal=meal,
            food_id=food.id,
            name=item.name,
            grams=round(item.grams, 1),
            method=method,
            **_from_food(food, item.grams),
        )
        session.add(entry)
        created.append(entry)
    await learn_from_saved(session, user_id, items)
    await session.commit()
    return [MealEntryOut.model_validate(e) for e in created]


async def _own_entry(session: AsyncSession, user_id: uuid.UUID, entry_id: uuid.UUID) -> MealEntry:
    entry = await session.scalar(
        select(MealEntry).where(MealEntry.id == entry_id, MealEntry.user_id == user_id)
    )
    if entry is None:
        raise NutritionError("Comida no encontrada")
    return entry


async def update_entry(
    session: AsyncSession, user_id: uuid.UUID, entry_id: uuid.UUID, data: MealEntryUpdate
) -> MealEntryOut:
    entry = await _own_entry(session, user_id, entry_id)
    sent = data.model_fields_set
    if "meal" in sent and data.meal:
        entry.meal = data.meal
    if "note" in sent:
        entry.note = data.note
    if "grams" in sent and data.grams is not None:
        if entry.food_id is None:
            raise NutritionError("Un añadido rápido no tiene gramos")
        food = await visible_food(session, user_id, entry.food_id)
        for key, value in _from_food(food, data.grams).items():
            setattr(entry, key, value)
        entry.grams = round(data.grams, 1)
        if entry.method == "racion":
            entry.method = "pesada"  # el usuario ha puesto los gramos exactos
    await session.commit()
    return MealEntryOut.model_validate(entry)


async def delete_entry(session: AsyncSession, user_id: uuid.UUID, entry_id: uuid.UUID) -> None:
    await session.delete(await _own_entry(session, user_id, entry_id))
    await session.commit()


# --- Objetivos, peso y resúmenes ---------------------------------------------------------


async def get_goal(session: AsyncSession, user_id: uuid.UUID) -> GoalOut:
    goal = await session.get(NutritionGoal, user_id)
    if goal is None:
        return GoalOut(goal="mantener")
    return GoalOut.model_validate(goal)


async def set_goal(session: AsyncSession, user_id: uuid.UUID, data: GoalIn) -> GoalOut:
    goal = await session.get(NutritionGoal, user_id)
    if goal is None:
        goal = NutritionGoal(user_id=user_id)
        session.add(goal)
    for key, value in data.model_dump().items():
        setattr(goal, key, value)
    await session.commit()
    return GoalOut.model_validate(goal)


async def _weight_on(session: AsyncSession, user: User, day: date) -> float | None:
    logged = await session.scalar(
        select(BodyWeightLog.weight_kg)
        .where(BodyWeightLog.user_id == user.id, BodyWeightLog.measured_on <= day)
        .order_by(BodyWeightLog.measured_on.desc())
        .limit(1)
    )
    return logged if logged is not None else user.weight_kg


async def _training_kcal(session: AsyncSession, user_id: uuid.UUID, day: date) -> float:
    start = datetime.combine(day, time.min, tzinfo=UTC)
    total = await session.scalar(
        select(func.coalesce(func.sum(TrainingSession.estimated_kcal), 0.0)).where(
            TrainingSession.user_id == user_id,
            TrainingSession.performed_at >= start,
            TrainingSession.performed_at < start + timedelta(days=1),
        )
    )
    return float(total or 0.0)


def _missing_profile(user: User, weight: float | None) -> list[str]:
    missing = []
    if weight is None:
        missing.append("peso")
    if user.height_cm is None:
        missing.append("altura")
    if user.birth_year is None:
        missing.append("año de nacimiento")
    return missing


async def target_for(
    session: AsyncSession, user: User, day: date
) -> tuple[TargetOut | None, list[str], float | None]:
    weight = await _weight_on(session, user, day)
    missing = _missing_profile(user, weight)
    if missing or weight is None or user.height_cm is None or user.birth_year is None:
        return None, missing, weight
    goal = await get_goal(session, user.id)
    sex: calc.Sex = "male" if user.sex == "male" else "female" if user.sex == "female" else None
    target = calc.daily_target(
        weight_kg=weight,
        height_cm=user.height_cm,
        age=calc.age_on(user.birth_year, day),
        sex=sex,
        activity_factor=goal.activity_factor,
        training_kcal=(
            await _training_kcal(session, user.id, day) if goal.activity_mode == "registro" else 0.0
        ),
        goal=goal.goal,
        protein_g_per_kg=goal.protein_g_per_kg,
        rate_kg_week=goal.rate_kg_week,
        target_weight_kg=goal.target_weight_kg,
        target_date=goal.target_date,
        today=day,
    )
    out = TargetOut.model_validate(target, from_attributes=True)
    out.activity_mode = "estimado" if goal.activity_mode == "estimado" else "registro"
    return out, [], weight


async def _entries(
    session: AsyncSession, user_id: uuid.UUID, start: date, end: date
) -> list[MealEntry]:
    rows = await session.scalars(
        select(MealEntry)
        .where(MealEntry.user_id == user_id, MealEntry.eaten_on >= start, MealEntry.eaten_on <= end)
        .order_by(MealEntry.eaten_on, MealEntry.created_at)
    )
    return list(rows.all())


def _totals(entries: list[MealEntry]) -> Totals:
    return Totals(
        kcal=round(sum(e.kcal for e in entries), 1),
        protein_g=round(sum(e.protein_g for e in entries), 1),
        carbs_g=round(sum(e.carbs_g for e in entries), 1),
        fat_g=round(sum(e.fat_g for e in entries), 1),
        fiber_g=round(sum(e.fiber_g or 0.0 for e in entries), 1),
    )


async def day_summary(session: AsyncSession, user: User, day: date) -> DayOut:
    entries = await _entries(session, user.id, day, day)
    meals: dict[str, list[MealEntryOut]] = {m: [] for m in MEALS}
    for e in entries:
        meals.setdefault(e.meal, []).append(MealEntryOut.model_validate(e))
    target, missing, weight = await target_for(session, user, day)
    exact = sum(e.kcal for e in entries if e.method in EXACT_METHODS)
    return DayOut(
        day=day,
        meals=meals,
        totals=_totals(entries),
        exact_kcal=round(exact, 1),
        estimated_kcal=round(sum(e.kcal for e in entries) - exact, 1),
        target=target,
        missing_profile=missing,
        weight_kg=weight,
    )


async def week_summary(session: AsyncSession, user: User, end: date) -> WeekOut:
    start = end - timedelta(days=6)
    by_day: dict[date, list[MealEntry]] = defaultdict(list)
    for e in await _entries(session, user.id, start, end):
        by_day[e.eaten_on].append(e)
    days: list[WeekDayOut] = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        totals = _totals(by_day.get(day, []))
        target, _, _ = await target_for(session, user, day)
        days.append(
            WeekDayOut(
                day=day,
                kcal=totals.kcal,
                protein_g=totals.protein_g,
                carbs_g=totals.carbs_g,
                fat_g=totals.fat_g,
                target_kcal=target.target_kcal if target else None,
                target_protein_g=target.protein_g if target else None,
                target_carbs_g=target.carbs_g if target else None,
                target_fat_g=target.fat_g if target else None,
            )
        )
    logged = [d for d in days if d.kcal > 0]
    targets = [d.target_kcal for d in days if d.target_kcal is not None]
    return WeekOut(
        days=days,
        average_kcal=round(sum(d.kcal for d in logged) / len(logged), 1) if logged else 0.0,
        average_target_kcal=round(sum(targets) / len(targets), 1) if targets else None,
    )


async def log_weight(
    session: AsyncSession,
    user: User,
    day: date,
    weight_kg: float,
    body_fat_pct: float | None = None,
    muscle_pct: float | None = None,
) -> None:
    row = await session.scalar(
        select(BodyWeightLog).where(
            BodyWeightLog.user_id == user.id, BodyWeightLog.measured_on == day
        )
    )
    if row is None:
        session.add(
            BodyWeightLog(
                user_id=user.id,
                measured_on=day,
                weight_kg=weight_kg,
                body_fat_pct=body_fat_pct,
                muscle_pct=muscle_pct,
            )
        )
    else:
        row.weight_kg = weight_kg
        # Sin porcentaje nuevo se conserva el medido antes ese día (no se borra).
        if body_fat_pct is not None:
            row.body_fat_pct = body_fat_pct
        if muscle_pct is not None:
            row.muscle_pct = muscle_pct
    latest = await session.scalar(
        select(func.max(BodyWeightLog.measured_on)).where(BodyWeightLog.user_id == user.id)
    )
    if latest is None or day >= latest:
        user.weight_kg = weight_kg  # el perfil refleja el peso más reciente
    await session.commit()


async def weight_history(
    session: AsyncSession, user_id: uuid.UUID, days: int, today: date
) -> WeightOut:
    rows = await session.scalars(
        select(BodyWeightLog)
        .where(
            BodyWeightLog.user_id == user_id,
            BodyWeightLog.measured_on >= today - timedelta(days=days),
        )
        .order_by(BodyWeightLog.measured_on)
    )
    logs = list(rows.all())
    trend = calc.weight_trend([(r.measured_on, r.weight_kg) for r in logs], today)
    return WeightOut(
        points=[
            WeightPointOut(
                measured_on=r.measured_on,
                weight_kg=r.weight_kg,
                body_fat_pct=r.body_fat_pct,
                muscle_pct=r.muscle_pct,
            )
            for r in logs
        ],
        latest_kg=trend.latest_kg,
        average_7d_kg=trend.average_7d_kg,
        change_week_kg=trend.change_week_kg,
        latest_body_fat_pct=next(
            (r.body_fat_pct for r in reversed(logs) if r.body_fat_pct is not None), None
        ),
        latest_muscle_pct=next(
            (r.muscle_pct for r in reversed(logs) if r.muscle_pct is not None), None
        ),
    )


async def delete_weight(session: AsyncSession, user_id: uuid.UUID, day: date) -> None:
    row = await session.scalar(
        select(BodyWeightLog).where(
            BodyWeightLog.user_id == user_id, BodyWeightLog.measured_on == day
        )
    )
    if row is None:
        raise NutritionError("No hay peso registrado ese día")
    await session.delete(row)
    await session.commit()


# --- Mis platos --------------------------------------------------------------------------


async def _template_out(
    session: AsyncSession, user_id: uuid.UUID, tpl: MealTemplate
) -> TemplateOut:
    kcal = 0.0
    for item in tpl.items:
        food = await session.scalar(
            select(Food).where(Food.id == uuid.UUID(str(item["food_id"])), _visible(user_id))
        )
        if food is not None:
            kcal += calc.scale_per_100g(food.kcal_100g, float(str(item["grams"]))) or 0.0
    items = [
        TemplateItem(food_id=uuid.UUID(str(i["food_id"])), grams=float(str(i["grams"])))
        for i in tpl.items
    ]
    return TemplateOut(id=tpl.id, name=tpl.name, items=items, kcal=round(kcal, 1))


async def list_templates(session: AsyncSession, user_id: uuid.UUID) -> list[TemplateOut]:
    rows = await session.scalars(
        select(MealTemplate).where(MealTemplate.user_id == user_id).order_by(MealTemplate.name)
    )
    return [await _template_out(session, user_id, t) for t in rows.all()]


async def create_template(
    session: AsyncSession, user_id: uuid.UUID, data: TemplateIn
) -> TemplateOut:
    for item in data.items:
        await visible_food(session, user_id, item.food_id)
    tpl = MealTemplate(
        user_id=user_id,
        name=data.name,
        items=[{"food_id": str(i.food_id), "grams": i.grams} for i in data.items],
    )
    session.add(tpl)
    await session.commit()
    return await _template_out(session, user_id, tpl)


async def _own_template(
    session: AsyncSession, user_id: uuid.UUID, tpl_id: uuid.UUID
) -> MealTemplate:
    tpl = await session.scalar(
        select(MealTemplate).where(MealTemplate.id == tpl_id, MealTemplate.user_id == user_id)
    )
    if tpl is None:
        raise NutritionError("Plato no encontrado")
    return tpl


async def delete_template(session: AsyncSession, user_id: uuid.UUID, tpl_id: uuid.UUID) -> None:
    await session.delete(await _own_template(session, user_id, tpl_id))
    await session.commit()


async def apply_template(
    session: AsyncSession, user_id: uuid.UUID, tpl_id: uuid.UUID, eaten_on: date, meal: Meal
) -> list[MealEntryOut]:
    tpl = await _own_template(session, user_id, tpl_id)
    out: list[MealEntryOut] = []
    for item in tpl.items:
        entry_in = MealEntryIn(
            eaten_on=eaten_on,
            meal=meal,
            food_id=uuid.UUID(str(item["food_id"])),
            grams=float(str(item["grams"])),
            method="pesada",
        )
        out.append(await add_entry(session, user_id, entry_in))
    return out


# --- Texto libre (IA) --------------------------------------------------------------------


USDA_CANDIDATES = 5
PLAUSIBLE_KCAL_RATIO = (0.6, 1.6)
PLAUSIBLE_KCAL_ABS = 60.0  # alimentos muy poco calóricos: margen absoluto


def _num(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def plausible_match(
    candidates: list[food_sources.FoodCandidate], estimate_kcal_100g: float | None
) -> food_sources.FoodCandidate | None:
    """El candidato USDA cuyas kcal/100 g más se acercan a la estimación, si es plausible.

    Evita errores graves de coincidencia ("coffee with milk" -> café soluble en polvo,
    549 kcal/100 g): si ningún candidato encaja, se queda la estimación de la IA.
    """
    if estimate_kcal_100g is None or not candidates:
        return None
    best = min(candidates, key=lambda c: abs(c.kcal_100g - estimate_kcal_100g))
    low, high = PLAUSIBLE_KCAL_RATIO
    within_ratio = estimate_kcal_100g > 0 and low <= best.kcal_100g / estimate_kcal_100g <= high
    within_abs = abs(best.kcal_100g - estimate_kcal_100g) <= PLAUSIBLE_KCAL_ABS
    return best if within_ratio or within_abs else None


async def _own_match(session: AsyncSession, user_id: uuid.UUID, name: str) -> Food | None:
    match: Food | None = await session.scalar(
        select(Food)
        .where(Food.owner_user_id == user_id, func.lower(Food.name) == name.strip().lower())
        .limit(1)
    )
    return match


async def _enrich(
    session: AsyncSession, user_id: uuid.UUID, raw: dict[str, object]
) -> ProposedItem:
    """Alimento propio > USDA (datos reales) > estimación de Claude."""
    name = str(raw.get("name") or "").strip()
    grams = float(str(raw.get("grams") or 0))
    own = await _own_match(session, user_id, name)
    if own is not None:
        return ProposedItem(
            name=own.name,
            grams=grams,
            kcal_100g=own.kcal_100g,
            protein_100g=own.protein_100g,
            carbs_100g=own.carbs_100g,
            fat_100g=own.fat_100g,
            fiber_100g=own.fiber_100g,
            source="custom",
            food_id=own.id,
        )
    name_en = str(raw.get("name_en") or "").strip()
    if name_en:
        try:
            matches = await food_sources.usda_search(name_en, limit=USDA_CANDIDATES)
        except food_sources.FoodSourceError:
            logger.warning("USDA no disponible; se usa la estimación de la IA para %s", name)
            matches = []
        best = plausible_match(matches, _num(raw.get("kcal_100g")))
        if best is not None:
            usda = await _cache(session, best)
            return ProposedItem(
                name=name,
                grams=grams,
                kcal_100g=usda.kcal_100g,
                protein_100g=usda.protein_100g,
                carbs_100g=usda.carbs_100g,
                fat_100g=usda.fat_100g,
                fiber_100g=usda.fiber_100g,
                source="usda",
                food_id=usda.id,
            )
    return ProposedItem.model_validate(
        {
            "name": name,
            "grams": grams,
            "kcal_100g": raw.get("kcal_100g", 0),
            "protein_100g": raw.get("protein_100g", 0),
            "carbs_100g": raw.get("carbs_100g", 0),
            "fat_100g": raw.get("fat_100g", 0),
            "fiber_100g": raw.get("fiber_100g"),
            "source": "ia",
        }
    )


async def parse_meal_text(
    session: AsyncSession, user_id: uuid.UUID, parsed: dict[str, object]
) -> ParseMealOut:
    raw_items = parsed.get("items")
    items = [
        await _enrich(session, user_id, raw)
        for raw in (raw_items if isinstance(raw_items, list) else [])
        if isinstance(raw, dict) and raw.get("name") and raw.get("grams")
    ]
    await session.commit()  # alimentos USDA cacheados
    unresolved = parsed.get("unresolved")
    return ParseMealOut(
        items=items,
        unresolved=[str(u) for u in unresolved] if isinstance(unresolved, list) else [],
        source="llm" if parsed.get("source") == "llm" else "fallback",
    )


# --- M10: texto libre con diccionario que aprende (IA solo para lo desconocido) ----------

MealFetcher = Callable[[str], Awaitable[dict[str, object]]]
PORTION_CORRECTION_RATIO = 0.15  # diferencia que cuenta como «mi ración es otra»


def _proposed(
    food: Food, grams: float, phrase: meal_dictionary.Phrase | None, single: bool
) -> ProposedItem:
    source = food.source if food.source in ("usda", "ia", "off", "custom") else "ia"
    return ProposedItem(
        name=food.name,
        grams=max(1.0, round(grams, 1)),
        kcal_100g=food.kcal_100g,
        protein_100g=food.protein_100g,
        carbs_100g=food.carbs_100g,
        fat_100g=food.fat_100g,
        fiber_100g=food.fiber_100g,
        source=source,
        food_id=food.id,
        alias=phrase.key if phrase is not None and single else None,
        quantity=phrase.quantity if phrase is not None and single else None,
    )


async def _alias(session: AsyncSession, user_id: uuid.UUID, key: str) -> FoodAlias | None:
    """Alias del usuario si existe; si no, el compartido."""
    rows = (
        await session.scalars(
            select(FoodAlias).where(
                FoodAlias.alias == key,
                or_(FoodAlias.owner_user_id == user_id, FoodAlias.owner_user_id.is_(None)),
            )
        )
    ).all()
    own = next((r for r in rows if r.owner_user_id is not None), None)
    return own or (rows[0] if rows else None)


async def _resolve_phrase(
    session: AsyncSession, user_id: uuid.UUID, phrase: meal_dictionary.Phrase
) -> list[ProposedItem] | None:
    alias = await _alias(session, user_id, phrase.key)
    if alias is None or not alias.items:
        return None
    foods: list[tuple[Food, float]] = []
    for food_id, grams in meal_dictionary.scale_items(phrase, alias.items):
        try:
            food = await visible_food(session, user_id, uuid.UUID(food_id))
        except (NutritionError, ValueError):
            return None  # alimento borrado: se vuelve a preguntar a la IA
        foods.append((food, grams))
    alias.uses = (alias.uses or 0) + 1
    single = len(foods) == 1
    return [_proposed(food, grams, phrase, single) for food, grams in foods]


async def _food_for_ai_item(
    session: AsyncSession, user_id: uuid.UUID, raw: dict[str, object]
) -> Food:
    """Alimento propio > ya aprendido > (USDA si está activado) > nuevo compartido «IA»."""
    name = str(raw.get("name") or "").strip()
    own = await _own_match(session, user_id, name)
    if own is not None:
        return own
    known = await _alias(session, user_id, meal_dictionary.alias_key(name))
    if known is not None and len(known.items) == 1:
        try:
            return await visible_food(session, user_id, uuid.UUID(str(known.items[0]["food_id"])))
        except (NutritionError, ValueError):
            pass
    name_en = str(raw.get("name_en") or "").strip()
    if settings.usda_enabled and name_en:
        try:
            matches = await food_sources.usda_search(name_en, limit=USDA_CANDIDATES)
        except food_sources.FoodSourceError:
            matches = []
        best = plausible_match(matches, _num(raw.get("kcal_100g")))
        if best is not None:
            return await _cache(session, best)
    food = Food(
        owner_user_id=None,  # lo calculó la IA una vez: queda para todos («estimado IA»)
        source="ia",
        name=name[:200],
        kcal_100g=_num(raw.get("kcal_100g")) or 0.0,
        protein_100g=_num(raw.get("protein_100g")) or 0.0,
        carbs_100g=_num(raw.get("carbs_100g")) or 0.0,
        fat_100g=_num(raw.get("fat_100g")) or 0.0,
        fiber_100g=_num(raw.get("fiber_100g")),
        servings=[],
    )
    session.add(food)
    await session.flush()
    key = meal_dictionary.alias_key(name)
    if key and await _alias(session, user_id, key) is None:
        session.add(
            FoodAlias(
                alias=key,
                owner_user_id=None,
                items=[{"food_id": str(food.id), "grams": _num(raw.get("grams")) or 100.0}],
                source="ia",
            )
        )
        await session.flush()
    return food


def _unit_factor(phrase: meal_dictionary.Phrase) -> float:
    """Cuántas «unidades del alias» hay en la frase (para guardar gramos por unidad)."""
    if phrase.grams is not None:
        return 1.0
    return phrase.quantity or 1.0


async def _learn_phrases(
    session: AsyncSession,
    user_id: uuid.UUID,
    unknown: list[meal_dictionary.Phrase],
    parsed: dict[str, object],
) -> dict[int, list[ProposedItem]]:
    raw_list = parsed.get("items")
    raw_items = [
        r
        for r in (raw_list if isinstance(raw_list, list) else [])
        if isinstance(r, dict) and r.get("name") and r.get("grams")
    ]
    by_phrase: dict[int, list[tuple[Food, float]]] = {}
    for raw in raw_items:
        index = raw.get("phrase")
        if not isinstance(index, int) or not 0 <= index < len(unknown):
            index = 0 if len(unknown) == 1 else -1
        food = await _food_for_ai_item(session, user_id, raw)
        by_phrase.setdefault(index, []).append((food, float(str(raw["grams"]))))
    result: dict[int, list[ProposedItem]] = {}
    for index, foods in by_phrase.items():
        phrase = unknown[index] if index >= 0 else None
        single = len(foods) == 1
        result[index] = [_proposed(food, grams, phrase, single) for food, grams in foods]
        if phrase is None or await _alias(session, user_id, phrase.key) is not None:
            continue
        factor = _unit_factor(phrase)
        session.add(
            FoodAlias(
                alias=phrase.key,
                owner_user_id=None,
                items=[{"food_id": str(f.id), "grams": round(g / factor, 1)} for f, g in foods],
                source="ia",
            )
        )
        await session.flush()
    return result


async def parse_meal(
    session: AsyncSession, user_id: uuid.UUID, text: str, fetch: MealFetcher
) -> ParseMealOut:
    """Texto libre -> propuesta. Primero el diccionario; la IA solo para lo desconocido."""
    phrases = meal_dictionary.split_phrases(text)
    known: dict[int, list[ProposedItem]] = {}
    unknown_idx: list[int] = []
    for i, phrase in enumerate(phrases):
        found = await _resolve_phrase(session, user_id, phrase)
        if found is None:
            unknown_idx.append(i)
        else:
            known[i] = found
    source = "rules"
    unresolved: list[str] = []
    extra: list[ProposedItem] = []
    if unknown_idx or not phrases:
        unknown = [phrases[i] for i in unknown_idx]
        prompt = " | ".join(p.raw for p in unknown) if unknown else text
        try:
            parsed = await fetch(prompt)
        except (httpx.HTTPError, ValueError):
            parsed = {"source": "fallback", "items": [], "unresolved": [p.raw for p in unknown]}
        learned = await _learn_phrases(session, user_id, unknown, parsed)
        for position, i in enumerate(unknown_idx):
            known[i] = learned.get(position, [])
        extra = learned.get(-1, [])
        raw_unresolved = parsed.get("unresolved")
        unresolved = [str(u) for u in raw_unresolved] if isinstance(raw_unresolved, list) else []
        source = "llm" if parsed.get("source") == "llm" else "fallback"
    await session.commit()
    items = [item for i in sorted(known) for item in known[i]] + extra
    return ParseMealOut(items=items, unresolved=unresolved, source=source)


async def learn_from_saved(
    session: AsyncSession, user_id: uuid.UUID, items: list[ProposedItem]
) -> None:
    """Si guardas otra ración para una frase conocida, se recuerda como tuya."""
    for item in items:
        if not item.alias or item.food_id is None:
            continue
        per_unit = item.grams / (item.quantity or 1.0)
        alias = await _alias(session, user_id, item.alias)
        if alias is None or len(alias.items) != 1:
            continue
        current = float(str(alias.items[0].get("grams") or 0)) or per_unit
        if abs(per_unit - current) / current <= PORTION_CORRECTION_RATIO:
            continue
        payload = [{"food_id": str(item.food_id), "grams": round(per_unit, 1)}]
        if alias.owner_user_id == user_id:
            alias.items = payload
        else:
            session.add(
                FoodAlias(alias=item.alias, owner_user_id=user_id, items=payload, source="user")
            )
