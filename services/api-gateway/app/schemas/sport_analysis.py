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


SportAnalysisOut.model_rebuild()
