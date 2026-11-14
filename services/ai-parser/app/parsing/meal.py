"""Texto libre de comida -> alimentos con gramos estimados (M5).

Claude estima raciones y valores por 100 g; el api-gateway los contrasta después con los
alimentos del usuario y con USDA (datos reales) antes de proponerlos.
"""

import logging

from pydantic import BaseModel, Field

from app.llm import factory
from app.llm.base import LLMProvider
from app.llm.errors import LLMError
from app.llm.structured import generate, user_data, with_user_data_rule
from app.schemas.meal import MealItem, MealParseResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Eres un dietista que convierte lo que alguien dice que ha comido en una lista de alimentos
con su cantidad en gramos, para contar calorías.

Para cada alimento devuelve:
- "name": nombre en español, simple y buscable ("pan de molde integral", "crema de cacahuete").
- "name_en": el mismo alimento en inglés, como aparecería en la base USDA
  ("bread, whole-wheat", "peanut butter, smooth").
- "grams": cantidad en gramos según raciones típicas en España (1 huevo L ≈ 60 g sin cáscara,
  1 rebanada de pan de molde ≈ 30 g, 1 cucharada de aceite ≈ 10 g, 1 cucharada de crema de
  cacahuete ≈ 16 g, 1 plato de pasta cocida ≈ 250 g). Si dicen gramos, usa esos gramos.
- "kcal_100g", "protein_100g", "carbs_100g", "fat_100g", "fiber_100g": valores típicos por
  100 g del alimento tal y como se come (cocido si está cocinado).

- "phrase": si el texto llega en fragmentos separados por " | ", el número del fragmento
  (empezando en 0) al que pertenece el alimento; si es un solo fragmento, 0.

Reglas:
- Separa los ingredientes visibles: "tostada con aceite" = pan + aceite.
- Si una cantidad es ambigua, elige la ración típica y añádelo a "unresolved".
- No inventes alimentos que no se mencionan.
""".strip()


class LlmMealItem(BaseModel):
    name: str = Field(min_length=1)
    name_en: str = Field(min_length=1)
    grams: float = Field(gt=0, le=5000)
    kcal_100g: float = Field(ge=0, le=950)
    protein_100g: float = Field(default=0, ge=0, le=100)
    carbs_100g: float = Field(default=0, ge=0, le=100)
    fat_100g: float = Field(default=0, ge=0, le=100)
    fiber_100g: float | None = Field(default=None, ge=0, le=100)
    phrase: int | None = Field(default=None, ge=0, le=30)


class LlmMeal(BaseModel):
    items: list[LlmMealItem] = Field(default_factory=list, max_length=30)
    unresolved: list[str] = Field(default_factory=list)


async def parse_meal_with_llm(provider: LLMProvider, text: str) -> MealParseResponse:
    meal = await generate(
        provider, with_user_data_rule(SYSTEM_PROMPT), user_data(text), LlmMeal, task="meal"
    )
    return MealParseResponse(
        source="llm",
        items=[MealItem(**item.model_dump()) for item in meal.items],
        unresolved=[u.strip() for u in meal.unresolved if u.strip()],
    )


async def parse_meal(text: str) -> MealParseResponse:
    provider = factory.get_provider()
    if provider is None:
        return MealParseResponse(source="fallback", items=[], unresolved=[text])
    try:
        return await parse_meal_with_llm(provider, text)
    except LLMError:
        logger.exception("Meal parse failed (%s)", provider.name)
        return MealParseResponse(source="fallback", items=[], unresolved=[text])
