import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Discipline = Literal["gym", "boxing", "running", "cycling", "swimming", "other"]


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


class ExerciseOut(CamelModel):
    id: uuid.UUID
    name: str
    sets: int | None
    reps: int | None
    weight_kg: float | None
    duration_minutes: float | None
    distance_meters: float | None
    volume_kg: float


class SessionIn(CamelModel):
    discipline: Discipline
    raw_text: str = Field(min_length=1)
    performed_at: datetime
    duration_minutes: int | None = Field(default=None, ge=0)
    note: str | None = None
    exercises: list[ExerciseIn] = Field(default_factory=list)


class SessionOut(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    volume_kg: float
    note: str | None
    created_at: datetime
    exercises: list[ExerciseOut]


class SessionListItem(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    volume_kg: float
