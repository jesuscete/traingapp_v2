import uuid

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.schemas.routine import DayType


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class PlanSplitOut(CamelModel):
    id: str
    name: str
    description: str


class PlanSetTargetOut(CamelModel):
    target_reps_min: int
    target_reps_max: int | None = None
    target_rest_seconds: int | None = None


class PlanExerciseOut(CamelModel):
    name: str
    exercise_id: uuid.UUID | None = None
    sets: list[PlanSetTargetOut] = Field(default_factory=list)


class PlanDayOut(CamelModel):
    day_of_week: int = Field(ge=1, le=7)
    day_type: DayType
    label: str | None = None
    discipline_id: uuid.UUID | None = None
    discipline_name: str | None = None
    duration_min: int | None = None
    exercises: list[PlanExerciseOut] = Field(default_factory=list)


class PlanSummaryOut(CamelModel):
    name: str
    days: list[PlanDayOut] = Field(default_factory=list)


class PlanDecisionIn(BaseModel):
    planRequestId: uuid.UUID
