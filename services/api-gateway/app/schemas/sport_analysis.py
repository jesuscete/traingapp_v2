import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class TargetStatusOut(CamelModel):
    key: str
    label: str
    value: float
    low: float
    high: float | None
    status: Literal["missing", "low", "ok", "high"]


class SuggestionOut(CamelModel):
    exercise_id: uuid.UUID
    name: str
    image_url: str | None = None


class GapOut(CamelModel):
    code: str
    severity: Literal["alta", "media", "baja"]
    message: str
    suggestions: list[SuggestionOut] = []


class SportAnalysisOut(CamelModel):
    sport: str
    label: str
    basis: Literal["historial", "rutina", "sin_datos"]
    weeks: float
    score: int
    patterns: list[TargetStatusOut]
    muscles: list[TargetStatusOut]
    rep_zones: list[TargetStatusOut]
    push_sets: float
    pull_sets: float
    pull_push_ratio: float | None
    gaps: list[GapOut]
    narrative: "SportNarrativeOut | None" = None
    adherence: "AdherenceOut | None" = None


class ExerciseAdherenceOut(CamelModel):
    exercise_id: uuid.UUID | None = None
    name: str
    planned_sets_week: float
    done_sets_week: float


class AdherenceOut(CamelModel):
    """Rutina frente a lo que el usuario registra de verdad (manda lo practicado)."""

    weeks: float
    pct: int  # % de las series planificadas que se hacen
    sessions: int
    history_score: int | None  # puntuación de lo practicado de verdad
    skipped: list[ExerciseAdherenceOut]  # de la rutina, hechos poco o nada
    off_plan: list[ExerciseAdherenceOut]  # practicados fuera de la rutina


class WeekFeedbackOut(CamelModel):
    """Frase breve tras un entreno: cómo va la semana frente al objetivo."""

    headline: str
    message: str
    score: int | None = None
    focus_code: str | None = None


class SportNarrativeOut(CamelModel):
    source: Literal["llm", "fallback"]
    resumen: str
    prioridades: list[str]


class AlternativeOut(CamelModel):
    exercise_id: uuid.UUID
    name: str
    similarity: float
    image_url: str | None = None
    is_custom: bool = False
    equipment: str | None = None
    equipment_label: str | None = None
    reason: str | None = None
    same_condition: bool = True


SportAnalysisOut.model_rebuild()


class RecommendationItemOut(CamelModel):
    exercise_id: uuid.UUID
    name: str
    image_url: str | None = None
    equipment: str
    equipment_label: str
    pattern: str
    pattern_label: str
    quality: str
    reason: str
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    note: str = ""


class RecommendationOut(CamelModel):
    """Ejercicios para un objetivo («mejorar la pegada») elegidos sin IA con el mapa del deporte."""

    sport: str
    sport_label: str
    goal_key: str | None
    goal_label: str
    focus: str
    items: list[RecommendationItemOut]
    summary: str
