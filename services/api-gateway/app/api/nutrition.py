import uuid
from datetime import UTC, date, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import food_sources
from app.core.database import get_db
from app.core.meal import fetch_meal_parse
from app.models import User
from app.schemas.nutrition import (
    ApplyTemplateIn,
    DayOut,
    FoodIn,
    FoodOut,
    GoalIn,
    GoalOut,
    MealBatchIn,
    MealEntryIn,
    MealEntryOut,
    MealEntryUpdate,
    ParseMealIn,
    ParseMealOut,
    TemplateIn,
    TemplateOut,
    WeekOut,
    WeightIn,
    WeightOut,
)
from app.services import nutrition
from app.services.nutrition import NutritionError

router = APIRouter(prefix="/nutrition", tags=["nutrition"])
Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _today() -> date:
    return datetime.now(UTC).date()


def _not_found(exc: NutritionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _invalid(exc: NutritionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))


# --- Alimentos ---------------------------------------------------------------------------


@router.get("/foods/search", response_model=list[FoodOut])
async def search_foods(
    db: Db, user: CurrentUser, q: Annotated[str, Query(min_length=2, max_length=80)]
) -> list[FoodOut]:
    """Tus alimentos y los ya usados primero; después caché local y Open Food Facts."""
    return await nutrition.search_foods(db, user.id, q)


@router.get("/foods/barcode/{barcode}", response_model=FoodOut)
async def food_by_barcode(barcode: str, db: Db, user: CurrentUser) -> FoodOut:
    if not barcode.isdigit() or not 6 <= len(barcode) <= 14:
        raise HTTPException(status_code=422, detail="Código de barras inválido")
    try:
        food = await nutrition.food_by_barcode(db, user.id, barcode)
    except food_sources.FoodSourceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Open Food Facts no responde; prueba a buscarlo por nombre",
        ) from None
    if food is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado: créalo con los datos de la etiqueta",
        )
    return food


@router.post("/foods", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def create_food(body: FoodIn, db: Db, user: CurrentUser) -> FoodOut:
    """Alimento propio con los valores de la etiqueta (por 100 g)."""
    return await nutrition.create_custom_food(db, user.id, body)


# --- Comidas -----------------------------------------------------------------------------


@router.post("/meals", response_model=MealEntryOut, status_code=status.HTTP_201_CREATED)
async def add_meal(body: MealEntryIn, db: Db, user: CurrentUser) -> MealEntryOut:
    try:
        return await nutrition.add_entry(db, user.id, body)
    except NutritionError as exc:
        raise _invalid(exc) from None


@router.post("/meals/batch", response_model=list[MealEntryOut], status_code=201)
async def add_meal_batch(body: MealBatchIn, db: Db, user: CurrentUser) -> list[MealEntryOut]:
    """Guarda una propuesta de texto libre ya revisada por el usuario."""
    try:
        return await nutrition.add_batch(
            db, user.id, body.eaten_on, body.meal, body.items, body.method
        )
    except NutritionError as exc:
        raise _invalid(exc) from None


@router.post("/meals/parse", response_model=ParseMealOut)
async def parse_meal(body: ParseMealIn, db: Db, user: CurrentUser) -> ParseMealOut:
    """Texto libre -> propuesta (no se guarda). La IA estima; USDA y tus alimentos corrigen."""
    try:
        parsed = await fetch_meal_parse(body.text)
    except (httpx.HTTPError, ValueError):
        return ParseMealOut(items=[], unresolved=[body.text], source="fallback")
    return await nutrition.parse_meal_text(db, user.id, parsed)


@router.put("/meals/{entry_id}", response_model=MealEntryOut)
async def update_meal(
    entry_id: uuid.UUID, body: MealEntryUpdate, db: Db, user: CurrentUser
) -> MealEntryOut:
    try:
        return await nutrition.update_entry(db, user.id, entry_id, body)
    except NutritionError as exc:
        raise _not_found(exc) if "no encontrad" in str(exc) else _invalid(exc) from None


@router.delete("/meals/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal(entry_id: uuid.UUID, db: Db, user: CurrentUser) -> None:
    try:
        await nutrition.delete_entry(db, user.id, entry_id)
    except NutritionError as exc:
        raise _not_found(exc) from None


@router.get("/day", response_model=DayOut)
async def day(db: Db, user: CurrentUser, day: date | None = None) -> DayOut:
    """Comidas del día, totales, kcal exactas/estimadas y objetivo (incluye los entrenos)."""
    return await nutrition.day_summary(db, user, day or _today())


@router.get("/week", response_model=WeekOut)
async def week(db: Db, user: CurrentUser, end: date | None = None) -> WeekOut:
    return await nutrition.week_summary(db, user, end or _today())


# --- Objetivo y peso ---------------------------------------------------------------------


@router.get("/goal", response_model=GoalOut)
async def get_goal(db: Db, user: CurrentUser) -> GoalOut:
    return await nutrition.get_goal(db, user.id)


@router.put("/goal", response_model=GoalOut)
async def set_goal(body: GoalIn, db: Db, user: CurrentUser) -> GoalOut:
    if body.goal == "corte" and body.target_weight_kg is None:
        raise HTTPException(status_code=422, detail="El corte necesita un peso objetivo")
    return await nutrition.set_goal(db, user.id, body)


@router.get("/weight", response_model=WeightOut)
async def weight(
    db: Db, user: CurrentUser, days: Annotated[int, Query(ge=7, le=365)] = 90
) -> WeightOut:
    return await nutrition.weight_history(db, user.id, days, _today())


@router.post("/weight", response_model=WeightOut, status_code=status.HTTP_201_CREATED)
async def log_weight(body: WeightIn, db: Db, user: CurrentUser) -> WeightOut:
    await nutrition.log_weight(db, user, body.measured_on, body.weight_kg)
    return await nutrition.weight_history(db, user.id, 90, _today())


@router.delete("/weight/{measured_on}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight(measured_on: date, db: Db, user: CurrentUser) -> None:
    try:
        await nutrition.delete_weight(db, user.id, measured_on)
    except NutritionError as exc:
        raise _not_found(exc) from None


# --- Mis platos --------------------------------------------------------------------------


@router.get("/templates", response_model=list[TemplateOut])
async def templates(db: Db, user: CurrentUser) -> list[TemplateOut]:
    return await nutrition.list_templates(db, user.id)


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(body: TemplateIn, db: Db, user: CurrentUser) -> TemplateOut:
    try:
        return await nutrition.create_template(db, user.id, body)
    except NutritionError as exc:
        raise _invalid(exc) from None


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: uuid.UUID, db: Db, user: CurrentUser) -> None:
    try:
        await nutrition.delete_template(db, user.id, template_id)
    except NutritionError as exc:
        raise _not_found(exc) from None


@router.post("/templates/{template_id}/apply", response_model=list[MealEntryOut], status_code=201)
async def apply_template(
    template_id: uuid.UUID, body: ApplyTemplateIn, db: Db, user: CurrentUser
) -> list[MealEntryOut]:
    try:
        return await nutrition.apply_template(db, user.id, template_id, body.eaten_on, body.meal)
    except NutritionError as exc:
        raise _not_found(exc) from None
