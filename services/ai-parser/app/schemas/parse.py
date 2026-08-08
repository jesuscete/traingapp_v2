import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

Discipline = Literal["gym", "boxing", "running", "cycling", "swimming", "other"]


class ExerciseDraft(BaseModel):
    name: str
    sets: int | None = None
    reps: int | None = None
    weight_kg: float | None = None


class ParseRequest(BaseModel):
    requestId: uuid.UUID
    rawText: str


class ParseResponse(BaseModel):
    rawText: str
    discipline: Discipline
    performedAt: datetime
    durationMinutes: int | None = None
    exercises: list[ExerciseDraft] = []
    confidence: float = 0.0
    unresolved: list[str] = []
