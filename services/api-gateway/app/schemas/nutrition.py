import re
import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

MEAL_ALIASES = {"snack": "media_manana", "almuerzo": "media_manana"}


def _meal_alias(value: object) -> object:
    """Compatibilidad: "snack" (nombre antiguo) y "almuerzo" se guardan como media mañana."""
    return MEAL_ALIASES.get(value, value) if isinstance(value, str) else value


# 5 tomas del día + "dia": registro agregado de todo el día (kcal y macros de otra app).
Meal = Annotated[
    Literal["desayuno", "media_manana", "comida", "merienda", "cena", "dia"],
    BeforeValidator(_meal_alias),
]
# Exactas: pesada (gramos de báscula), etiqueta (valores copiados del envase).
# Estimadas: racion (raciones típicas), rapida (kcal sueltas), ia (texto libre).
Method = Literal["pesada", "etiqueta", "racion", "rapida", "ia"]
EXACT_METHODS: frozenset[str] = frozenset({"pesada", "etiqueta"})
GoalType = Literal["perder", "mantener", "ganar", "corte"]
# registro: factor = vida diaria sin deporte + kcal reales de los entrenos registrados.
# estimado: factor que ya incluye el deporte; no se suman los entrenos (no se cuentan dos veces).
ActivityMode = Literal["registro", "estimado"]


def _camel(name: str) -> str:
    """camelCase sin mayúscula tras un número: kcal_100g -> kcal100g (no kcal100G)."""
    return re.sub(r"(\d)([A-Z])", lambda m: m.group(1) + m.group(2).lower(), to_camel(name))


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_camel, from_attributes=True)


class Serving(CamelModel):
    label: str = Field(min_length=1, max_length=60)
    grams: float = Field(gt=0, le=5000)


class FoodOut(CamelModel):
    id: uuid.UUID
    source: str
    name: str
    brand: str | None
    store: str | None = None
    barcode: str | None
    kcal_100g: float
    protein_100g: float
    carbs_100g: float
    fat_100g: float
    fiber_100g: float | None
    sugar_100g: float | None
    servings: list[Serving] = []
    is_custom: bool = False


class FoodFacetsOut(CamelModel):
    """Opciones de filtro de la búsqueda de alimentos."""

    stores: list[str]
    brands: list[str]


class FoodIn(CamelModel):
    """Alimento propio con los valores de la etiqueta (por 100 g)."""

    name: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=120)
    barcode: str | None = Field(default=None, max_length=32)
    kcal_100g: float = Field(ge=0, le=950)
    protein_100g: float = Field(default=0, ge=0, le=100)
    carbs_100g: float = Field(default=0, ge=0, le=100)
    fat_100g: float = Field(default=0, ge=0, le=100)
    fiber_100g: float | None = Field(default=None, ge=0, le=100)
    sugar_100g: float | None = Field(default=None, ge=0, le=100)
    servings: list[Serving] = Field(default_factory=list, max_length=10)


class MealEntryIn(CamelModel):
    """Tres formas: alimento + gramos (báscula), alimento + raciones, o añadido rápido."""

    eaten_on: date
    meal: Meal
    food_id: uuid.UUID | None = None
    grams: float | None = Field(default=None, gt=0, le=5000)
    servings: float | None = Field(default=None, gt=0, le=50)
    serving_label: str | None = None
    # Añadido rápido (sin alimento): kcal obligatorias.
    name: str | None = Field(default=None, max_length=200)
    kcal: float | None = Field(default=None, ge=0, le=10000)
    protein_g: float | None = Field(default=None, ge=0, le=1000)
    carbs_g: float | None = Field(default=None, ge=0, le=1000)
    fat_g: float | None = Field(default=None, ge=0, le=1000)
    method: Method | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _one_mode(self) -> "MealEntryIn":
        if self.food_id is not None:
            if (self.grams is None) == (self.servings is None):
                raise ValueError("Con un alimento indica gramos o raciones (solo uno)")
        elif self.kcal is None or not self.name:
            raise ValueError("Sin alimento, el añadido rápido necesita nombre y kcal")
        return self


class MealEntryUpdate(CamelModel):
    meal: Meal | None = None
    grams: float | None = Field(default=None, gt=0, le=5000)
    note: str | None = Field(default=None, max_length=500)


class MealEntryOut(CamelModel):
    id: uuid.UUID
    eaten_on: date
    meal: str
    food_id: uuid.UUID | None
    name: str
    grams: float | None
    kcal: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float | None
    method: str
    note: str | None


class ProposedItem(CamelModel):
    """Alimento propuesto desde texto libre (no guardado hasta confirmar)."""

    name: str = Field(min_length=1, max_length=200)
    grams: float = Field(gt=0, le=5000)
    kcal_100g: float = Field(ge=0, le=950)
    protein_100g: float = Field(default=0, ge=0, le=100)
    carbs_100g: float = Field(default=0, ge=0, le=100)
    fat_100g: float = Field(default=0, ge=0, le=100)
    fiber_100g: float | None = Field(default=None, ge=0, le=100)
    source: Literal["usda", "ia", "off", "custom"] = "ia"
    food_id: uuid.UUID | None = None
    # Frase del diccionario de la que sale (para recordar tu ración si la cambias).
    alias: str | None = Field(default=None, max_length=200)
    quantity: float | None = Field(default=None, gt=0, le=100)


class ParseMealIn(CamelModel):
    text: str = Field(min_length=2, max_length=1000)


class ParseMealOut(CamelModel):
    items: list[ProposedItem]
    unresolved: list[str] = []
    # "rules" = todo salió del diccionario, sin IA.
    source: Literal["llm", "fallback", "rules"]


class MealBatchIn(CamelModel):
    eaten_on: date
    meal: Meal
    items: list[ProposedItem] = Field(min_length=1, max_length=30)
    method: Method = "ia"


class Totals(CamelModel):
    kcal: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0


class TargetOut(CamelModel):
    bmr: float
    daily_activity_kcal: float
    training_kcal: float
    maintenance_kcal: float
    adjustment_kcal: float
    target_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    rate_kg_week: float
    notes: list[str]
    activity_mode: ActivityMode = "registro"


class DayOut(CamelModel):
    day: date
    meals: dict[str, list[MealEntryOut]]
    totals: Totals
    exact_kcal: float
    estimated_kcal: float
    target: TargetOut | None
    missing_profile: list[str] = []
    weight_kg: float | None


class WeekDayOut(CamelModel):
    day: date
    kcal: float
    protein_g: float
    target_kcal: float | None


class WeekOut(CamelModel):
    days: list[WeekDayOut]
    average_kcal: float
    average_target_kcal: float | None


class WeightIn(CamelModel):
    measured_on: date
    weight_kg: float = Field(gt=20, lt=400)
    # Báscula de bioimpedancia (opcional).
    body_fat_pct: float | None = Field(default=None, ge=2, le=70)
    muscle_pct: float | None = Field(default=None, ge=10, le=80)


class WeightPointOut(CamelModel):
    measured_on: date
    weight_kg: float
    body_fat_pct: float | None = None
    muscle_pct: float | None = None


class WeightOut(CamelModel):
    points: list[WeightPointOut]
    latest_kg: float | None
    average_7d_kg: float | None
    change_week_kg: float | None
    # Última medición de composición corporal (puede ser de otro día que el último peso).
    latest_body_fat_pct: float | None = None
    latest_muscle_pct: float | None = None


class GoalIn(CamelModel):
    goal: GoalType
    target_weight_kg: float | None = Field(default=None, gt=20, lt=400)
    target_date: date | None = None
    rate_kg_week: float | None = Field(default=None, ge=0, le=2)
    protein_g_per_kg: float = Field(default=2.0, ge=0.8, le=3.5)
    activity_factor: float = Field(default=1.4, ge=1.1, le=2.0)
    activity_mode: ActivityMode = "registro"


class GoalOut(GoalIn):
    pass


class TemplateItem(CamelModel):
    food_id: uuid.UUID
    grams: float = Field(gt=0, le=5000)


class TemplateIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    items: list[TemplateItem] = Field(min_length=1, max_length=30)


class TemplateOut(CamelModel):
    id: uuid.UUID
    name: str
    items: list[TemplateItem]
    kcal: float


class ApplyTemplateIn(CamelModel):
    eaten_on: date
    meal: Meal
