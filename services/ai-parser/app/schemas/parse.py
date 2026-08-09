from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

DISCIPLINES: tuple[str, ...] = (
    "gym",
    "boxing",
    "running",
    "cycling",
    "swimming",
    "other",
)
Discipline = Literal[
    "gym", "boxing", "running", "cycling", "swimming", "other"
]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class ExerciseDraft(CamelModel):
    name: str
    sets: int | None = None
    reps: int | None = None
    per_set_reps: list[int] | None = None
    weight_kg: float | None = None


class ParseRequest(BaseModel):
    requestId: str
    rawText: str


class ParseResponse(CamelModel):
    rawText: str
    discipline: Discipline
    performedAt: str
    durationMinutes: int | None = None
    exercises: list[ExerciseDraft] = []
    suggestedRpe: float | None = None
    confidence: float = 0.0
    unresolved: list[str] = []
