import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class HistorySetOut(CamelModel):
    set_number: int
    set_type: str
    is_warmup: bool
    reps: int | None
    weight_kg: float | None
    rpe: int | None
    e1rm_kg: float | None = Field(alias="e1rmKg")


class HistorySessionOut(CamelModel):
    session_id: uuid.UUID
    performed_at: datetime
    sets: list[HistorySetOut]


class ExerciseRecordsOut(CamelModel):
    max_weight_kg: float | None
    best_e1rm_kg: float | None = Field(alias="bestE1rmKg")
    max_reps: int | None
    best_set_volume_kg: float | None
    best_session_volume_kg: float | None


class ProgressPointOut(CamelModel):
    performed_at: datetime
    best_e1rm_kg: float | None = Field(alias="bestE1rmKg")
    top_weight_kg: float | None
    volume_kg: float


class ExerciseHistoryOut(CamelModel):
    exercise_id: uuid.UUID
    records: ExerciseRecordsOut
    progress: list[ProgressPointOut]
    sessions: list[HistorySessionOut]
