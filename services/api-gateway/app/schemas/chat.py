import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ChatMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatEnqueueOut(BaseModel):
    requestId: uuid.UUID
    status: str


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class ExerciseDraftOut(CamelModel):
    name: str
    sets: int | None = None
    reps: int | None = None
    per_set_reps: list[int] | None = None
    weight_kg: float | None = None


class WorkoutDraftOut(CamelModel):
    raw_text: str
    discipline: str
    performed_at: datetime
    duration_minutes: int | None = None
    exercises: list[ExerciseDraftOut] = Field(default_factory=list)
    suggested_rpe: float | None = None
    confidence: float = 0.0
    unresolved: list[str] = Field(default_factory=list)


class ChatDraftOut(BaseModel):
    requestId: uuid.UUID
    draft: WorkoutDraftOut


class ChatMessageOut(BaseModel):
    mode: Literal["direct", "live", "confirm"]
    requestId: uuid.UUID | None = None
    liveSessionId: uuid.UUID | None = None
    startedAt: datetime | None = None
    entriesCount: int = 0
    draft: WorkoutDraftOut | None = None


class ChatConfirmIn(BaseModel):
    requestId: uuid.UUID
    suggestedRpe: float | None = Field(default=None, ge=1, le=10)
    perceivedFatigue: float | None = Field(default=None, ge=1, le=10)
    performedAt: datetime | None = None
    durationMinutes: int | None = Field(default=None, ge=0)
    distanceMeters: float | None = Field(default=None, ge=0)
    workoutType: str | None = Field(default=None, max_length=20)
    exercises: list[ExerciseDraftOut] | None = None


class ChatCancelIn(BaseModel):
    requestId: uuid.UUID
