"""Entrenos del reloj sin catalogar (ADR-012)."""

import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.metrics import SessionMetrics
from app.schemas.session import CamelModel, Discipline, ExerciseIn


class PendingWatchOut(CamelModel):
    id: uuid.UUID
    performed_at: datetime
    duration_minutes: int | None
    estimated_kcal: float | None
    avg_heart_rate: float | None
    max_heart_rate: float | None
    distance_meters: float | None
    # Lo que dijo el reloj («training» / «cardio_training», «hiit»…), para orientar.
    sport: str | None = None
    sub_sport: str | None = None
    trimp: float | None = None


class PendingWatchListOut(CamelModel):
    items: list[PendingWatchOut]


class ClassifyIn(CamelModel):
    discipline: Discipline
    note: str | None = Field(default=None, max_length=2000)
    intensity: int | None = Field(default=None, ge=1, le=10)
    metrics: SessionMetrics | None = None
    # None = no tocar; lista (aunque vacía) = sustituye los ejercicios.
    exercises: list[ExerciseIn] | None = None


class ClassifyPreviewIn(CamelModel):
    text: str = Field(min_length=3, max_length=2000)


class ClassifyPreviewOut(CamelModel):
    discipline: Discipline | None
    exercises: list[ExerciseIn]
    metrics: SessionMetrics | None = None
    intensity: int | None = None
    unresolved: list[str] = Field(default_factory=list)
