from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

DayType = Literal["gimnasio", "deporte", "descanso"]
Goal = Literal["aesthetic", "performance"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class SportIn(CamelModel):
    name: str
    days: list[int] = Field(default_factory=list)  # 1=lunes ... 7=domingo
    duration_min: int | None = None


class SplitContextIn(CamelModel):
    sports: list[SportIn] = Field(default_factory=list)
    gym_days: int = Field(default=0, ge=0, le=7)


class SplitOption(CamelModel):
    id: str
    name: str
    description: str


class SplitResponse(CamelModel):
    options: list[SplitOption] = Field(default_factory=list)


class PlanSetTarget(CamelModel):
    target_reps_min: int = Field(ge=1)
    target_reps_max: int | None = Field(default=None, ge=1)
    target_rest_seconds: int | None = Field(default=None, ge=0)


class PlanExercise(CamelModel):
    name: str
    sets: list[PlanSetTarget] = Field(default_factory=list)


class PlanDay(CamelModel):
    day_of_week: int = Field(ge=1, le=7)
    day_type: DayType
    label: str | None = None
    discipline: str | None = None  # normalized_name de la disciplina en dias deporte
    duration_min: int | None = None
    exercises: list[PlanExercise] = Field(default_factory=list)


class PlanGenerateIn(CamelModel):
    sports: list[SportIn] = Field(default_factory=list)
    gym_days: int = Field(default=0, ge=0, le=7)
    split_id: str | None = None
    goal: Goal = "aesthetic"
    catalog: list[str] = Field(default_factory=list)
    system_prompt: str | None = None  # plantilla con placeholders {deportes}, {objetivo}, ...


class PlanResponse(CamelModel):
    name: str
    days: list[PlanDay] = Field(default_factory=list)
