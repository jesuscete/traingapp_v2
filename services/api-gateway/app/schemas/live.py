import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class LiveSetOut(CamelModel):
    set_number: int
    set_type: str = "normal"
    target_reps_min: int | None = None
    target_reps_max: int | None = None
    reps: int | None = None
    weight: float | None = None
    suggested_weight: float | None = None
    is_warmup: bool = False


class LiveExerciseOut(CamelModel):
    name: str
    exercise_id: uuid.UUID | None = None
    order_index: int = 0
    routine_exercise_id: uuid.UUID | None = None
    sets: list[LiveSetOut]


class LiveSessionOut(CamelModel):
    live_session_id: uuid.UUID
    started_at: datetime
    origin: str = "free"
    discipline: str | None = None
    routine_day_id: uuid.UUID | None = None
    exercises: list[LiveExerciseOut] = Field(default_factory=list)
    entries: list[str] = Field(default_factory=list)
    entries_count: int = 0


class LiveStartIn(CamelModel):
    routine_day_id: uuid.UUID | None = None


class LiveSetUpdateIn(CamelModel):
    exercise_index: int = Field(ge=0)
    set_number: int = Field(ge=1)
    weight: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=1)


class LiveSetIn(CamelModel):
    set_number: int = Field(ge=1)
    weight: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=1)


class LiveAddExerciseIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    exercise_id: uuid.UUID | None = None
    sets: list[LiveSetIn] = Field(min_length=1)


class LiveAddSetIn(CamelModel):
    exercise_index: int = Field(ge=0)
    set_number: int = Field(ge=1)
    weight: float | None = Field(default=None, ge=0)
    reps: int | None = Field(default=None, ge=1)


class LiveFinishIn(CamelModel):
    duration_minutes: int | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    note: str | None = None
    performed_at: datetime | None = None
    keep_sets_without_weight: bool = False


LiveOrigin = Literal["free", "routine"]
