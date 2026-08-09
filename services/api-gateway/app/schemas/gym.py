import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

SetType = Literal[
    "normal", "calentamiento", "dropset", "al_fallo", "amrap", "isometrico"
]
WeightUnit = Literal["kg", "lb"]
Side = Literal["left", "right", "both"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class SetEntryIn(CamelModel):
    entry_order: int = Field(ge=0)
    reps: int | None = Field(default=None, ge=1)
    weight: float | None = Field(default=None, ge=0)
    weight_unit: WeightUnit = "kg"
    duration_seconds: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    rpe: int | None = Field(default=None, ge=1, le=10)
    side: Side = "both"


class WorkoutSetIn(CamelModel):
    set_number: int = Field(ge=1)
    set_type: SetType = "normal"
    rest_seconds: int | None = Field(default=None, ge=0)
    is_warmup: bool = False
    entries: list[SetEntryIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_entries(self) -> "WorkoutSetIn":
        if self.set_type == "normal" and len(self.entries) != 1:
            raise ValueError(
                "Una serie normal debe tener exactamente 1 set_entry"
            )
        if self.set_type == "dropset" and len(self.entries) < 2:
            raise ValueError("Un dropset debe tener 2+ set_entry")
        return self


class WorkoutExerciseIn(CamelModel):
    exercise_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    order_index: int = 0
    superset_group_id: uuid.UUID | None = None
    sets: list[WorkoutSetIn] = Field(min_length=1)


class GymSessionIn(CamelModel):
    raw_text: str = Field(min_length=1)
    performed_at: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    calories: float | None = Field(default=None, ge=0)
    note: str | None = None
    details: dict[str, object] | None = None
    exercises: list[WorkoutExerciseIn] = Field(min_length=1)


class SetEntryOut(CamelModel):
    id: uuid.UUID
    entry_order: int
    reps: int | None
    weight: float | None
    weight_unit: str
    duration_seconds: float | None
    distance_meters: float | None
    rpe: int | None
    side: str


class WorkoutSetOut(CamelModel):
    id: uuid.UUID
    set_number: int
    set_type: str
    rest_seconds: int | None
    is_warmup: bool
    volume_kg: float
    entries: list[SetEntryOut]


class WorkoutExerciseOut(CamelModel):
    id: uuid.UUID
    session_id: uuid.UUID
    exercise_id: uuid.UUID | None
    name: str
    order_index: int
    superset_group_id: uuid.UUID | None
    volume_kg: float
    sets: list[WorkoutSetOut]


class WorkoutSessionSummaryOut(CamelModel):
    session_id: uuid.UUID
    total_volume: float
    avg_rpe: float | None
    sets_count: int
    duration_min: int


class MuscleImpactOut(CamelModel):
    muscle_group: str
    activation: float


class GymSessionOut(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    start_time: datetime | None = None
    end_time: datetime | None = None
    intensity: int | None = None
    fatigue: int | None = None
    duration_minutes: int | None = None
    volume_kg: float
    estimated_kcal: float | None = None
    calories: float | None = None
    note: str | None = None
    details: dict[str, object] | None = None
    created_at: datetime
    workout_exercises: list[WorkoutExerciseOut]
    summary: WorkoutSessionSummaryOut | None = None
    muscle_impacts: list[MuscleImpactOut] = Field(default_factory=list)
