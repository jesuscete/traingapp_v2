import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# Enum de disciplinas del catalogo canonical (`discipline_seed.DISCIPLINE_SEED`).
# Mantener sincronizado con la semilla: no hay validacion dinamica en schemas.
Discipline = Literal[
    "gym",
    "calisthenics",
    "boxing",
    "martial_arts",
    "running",
    "cycling",
    "swimming",
    "climbing",
    "football",
    "basketball",
    "volleyball",
    "cricket",
    "baseball",
    "hockey",
    "rugby",
    "handball",
    "badminton",
    "table_tennis",
    "tennis",
    "ski_snowboard",
    "golf",
    "other",
]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class ExerciseIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    sets: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=1)
    weight_kg: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    details: dict[str, object] | None = None


class ExerciseOut(CamelModel):
    id: uuid.UUID
    name: str
    sets: int | None
    reps: int | None
    weight_kg: float | None
    duration_minutes: float | None
    distance_meters: float | None
    volume_kg: float
    details: dict[str, object] | None = None


class SessionIn(CamelModel):
    discipline: Discipline
    raw_text: str = Field(min_length=1)
    performed_at: datetime
    duration_minutes: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    note: str | None = None
    routine_day_id: uuid.UUID | None = None
    details: dict[str, object] | None = None
    exercises: list[ExerciseIn] = Field(default_factory=list)


class MuscleImpactOut(CamelModel):
    muscle_group: str
    activation: float
    zone: str = "other"


class SessionOut(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    distance_meters: float | None = None
    volume_kg: float
    estimated_kcal: float | None = None
    intensity: int | None = None
    fatigue: int | None = None
    note: str | None
    details: dict[str, object] | None = None
    created_at: datetime
    exercises: list[ExerciseOut]
    muscle_impacts: list[MuscleImpactOut] = Field(default_factory=list)


class SessionListItem(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    volume_kg: float
    estimated_kcal: float | None = None
    intensity: int | None = None
    fatigue: int | None = None
