from typing import Literal

from pydantic import BaseModel, Field


class MealParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class MealItem(BaseModel):
    name: str
    name_en: str
    grams: float
    kcal_100g: float
    protein_100g: float = 0
    carbs_100g: float = 0
    fat_100g: float = 0
    fiber_100g: float | None = None
    phrase: int | None = None  # fragmento del texto (separado por " | ") al que pertenece


class MealParseResponse(BaseModel):
    source: Literal["llm", "fallback"] = "llm"
    items: list[MealItem] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
