from typing import Literal

from pydantic import BaseModel, Field


class SportNarrativeRequest(BaseModel):
    sport_label: str = Field(alias="sportLabel")
    analysis: dict[str, object]


class SportNarrativeResponse(BaseModel):
    source: Literal["llm", "fallback"] = "llm"
    resumen: str
    prioridades: list[str]
