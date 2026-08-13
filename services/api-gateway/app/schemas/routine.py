import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.schemas.gym import SetType

DayType = Literal["gimnasio", "deporte", "descanso"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class MuscleLoadOut(CamelModel):
    muscle_group: str
    load: float


class DisciplineOut(CamelModel):
    id: uuid.UUID
    name: str
    normalized_name: str
    met: float
    category: str
    kind: str
    muscle_loads: list[MuscleLoadOut] = Field(default_factory=list)


class RoutineSetIn(CamelModel):
    set_number: int = Field(ge=1)
    set_type: SetType = "normal"
    target_reps_min: int | None = Field(default=None, ge=1)
    target_reps_max: int | None = Field(default=None, ge=1)
    target_rest_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _validate_reps_range(self) -> "RoutineSetIn":
        if (
            self.target_reps_min is not None
            and self.target_reps_max is not None
            and self.target_reps_max < self.target_reps_min
        ):
            raise ValueError("target_reps_max debe ser >= target_reps_min")
        return self


class RoutineExerciseIn(CamelModel):
    exercise_id: uuid.UUID
    order_index: int = 0
    superset_group_id: uuid.UUID | None = None
    sets: list[RoutineSetIn] = Field(min_length=1)


class RoutineDayIn(CamelModel):
    day_of_week: int = Field(ge=1, le=7)
    day_type: DayType
    label: str | None = Field(default=None, max_length=80)
    discipline_id: uuid.UUID | None = None
    target_duration_min: int | None = Field(default=None, ge=0)
    notes: str | None = None
    exercises: list[RoutineExerciseIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_conditional_fields(self) -> "RoutineDayIn":
        if self.day_type == "deporte":
            if self.discipline_id is None:
                raise ValueError("Un día de deporte requiere discipline_id")
            if self.exercises:
                raise ValueError("Un día de deporte no puede tener ejercicios de gimnasio")
            if self.target_duration_min is not None and self.target_duration_min <= 0:
                raise ValueError("target_duration_min debe ser > 0")
        elif self.day_type == "gimnasio":
            if self.discipline_id is not None or self.target_duration_min is not None:
                raise ValueError(
                    "Un día de gimnasio no admite discipline_id ni target_duration_min"
                )
            if not self.exercises:
                raise ValueError("Un día de gimnasio necesita al menos un ejercicio")
        else:  # descanso
            if (
                self.discipline_id is not None
                or self.target_duration_min is not None
                or self.exercises
            ):
                raise ValueError("Un día de descanso no admite disciplina, duración ni ejercicios")
        return self


class RoutineIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    days: list[RoutineDayIn] = Field(default_factory=list)


class RoutineDayUpsert(CamelModel):
    day_type: DayType
    label: str | None = Field(default=None, max_length=80)
    discipline_id: uuid.UUID | None = None
    target_duration_min: int | None = Field(default=None, ge=0)
    notes: str | None = None
    exercises: list[RoutineExerciseIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_conditional_fields(self) -> "RoutineDayUpsert":
        if self.day_type == "deporte":
            if self.discipline_id is None:
                raise ValueError("Un día de deporte requiere discipline_id")
            if self.exercises:
                raise ValueError("Un día de deporte no puede tener ejercicios de gimnasio")
        elif self.day_type == "gimnasio":
            if self.discipline_id is not None or self.target_duration_min is not None:
                raise ValueError(
                    "Un día de gimnasio no admite discipline_id ni target_duration_min"
                )
            if not self.exercises:
                raise ValueError("Un día de gimnasio necesita al menos un ejercicio")
        else:  # descanso
            if (
                self.discipline_id is not None
                or self.target_duration_min is not None
                or self.exercises
            ):
                raise ValueError("Un día de descanso no admite disciplina, duración ni ejercicios")
        return self


class RoutineUpdateIn(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None


class RoutineSetOut(CamelModel):
    id: uuid.UUID
    set_number: int
    set_type: str
    target_reps_min: int | None
    target_reps_max: int | None = None
    target_rest_seconds: int | None = None


class RoutineExerciseOut(CamelModel):
    id: uuid.UUID
    exercise_id: uuid.UUID | None
    name: str | None = None
    order_index: int
    superset_group_id: uuid.UUID | None = None
    sets: list[RoutineSetOut]


class RoutineDayOut(CamelModel):
    id: uuid.UUID
    day_of_week: int
    day_type: str
    label: str | None = None
    discipline_id: uuid.UUID | None = None
    discipline_name: str | None = None
    target_duration_min: int | None = None
    notes: str | None = None
    exercises: list[RoutineExerciseOut]


class RoutineOut(CamelModel):
    id: uuid.UUID
    name: str
    is_active: bool
    created_at: datetime
    days: list[RoutineDayOut]


class RoutineReviewItemIn(CamelModel):
    dia_semana: str
    tipo: str
    nombre: str
    grupos_musculares: list[str] = Field(default_factory=list)
    series: int | None = None
    repeticiones: int | None = None
    duracion_min: int | None = None


class RoutineReviewIn(CamelModel):
    routine_name: str = "Rutina"
    days: list[RoutineReviewItemIn] = Field(default_factory=list)


class SolapamientoOut(CamelModel):
    descripcion: str = ""
    grupos: list[str] = Field(default_factory=list)
    dias: list[str] = Field(default_factory=list)


class RoutineReviewOut(CamelModel):
    puntos_fuerte: list[str] = Field(default_factory=list)
    solapamientos: list[SolapamientoOut] = Field(default_factory=list)
    sugerencias: list[str] = Field(default_factory=list)
