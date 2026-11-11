"""Métricas específicas por tipo de deporte (RF-01), guardadas en `details["metrics"]`.

Unión discriminada por `kind`. La fuerza no usa este esquema: va al modelo gym
(ADR-001).
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

MetricsKind = Literal["combat", "endurance", "climbing", "generic"]

# Disciplina -> tipo de métricas esperado. Lo que no aparece usa "generic".
DISCIPLINE_METRICS: dict[str, MetricsKind] = {
    "boxing": "combat",
    "martial_arts": "combat",
    "running": "endurance",
    "cycling": "endurance",
    "swimming": "endurance",
    "ski_snowboard": "endurance",
    "climbing": "climbing",
}

CombatBlockType = Literal["saco", "sparring", "manoplas", "comba", "sombra", "tecnica", "fisico"]
ClimbingStyle = Literal["boulder", "via", "autobelay", "exterior"]

MAX_ROUNDS = 50
MAX_ROUND_SECONDS = 600
MAX_BLOCK_MINUTES = 300


def metrics_kind_for(discipline: str) -> MetricsKind:
    return DISCIPLINE_METRICS.get(discipline, "generic")


class _Camel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")


class CombatBlock(_Camel):
    type: CombatBlockType
    rounds: int | None = Field(default=None, ge=1, le=MAX_ROUNDS)
    round_seconds: int | None = Field(default=None, ge=10, le=MAX_ROUND_SECONDS)
    minutes: float | None = Field(default=None, gt=0, le=MAX_BLOCK_MINUTES)
    strikes: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _has_duration(self) -> "CombatBlock":
        if self.minutes is None and self.rounds is None:
            raise ValueError("Cada bloque necesita rounds o minutos")
        return self

    def total_minutes(self) -> float:
        if self.minutes is not None:
            return self.minutes
        rounds = self.rounds or 0
        return rounds * (self.round_seconds or 180) / 60


class CombatMetrics(_Camel):
    kind: Literal["combat"] = "combat"
    blocks: list[CombatBlock] = Field(min_length=1, max_length=20)


class EnduranceMetrics(_Camel):
    kind: Literal["endurance"] = "endurance"
    distance_meters: float | None = Field(default=None, gt=0, le=1_000_000)
    avg_heart_rate: int | None = Field(default=None, ge=30, le=230)
    max_heart_rate: int | None = Field(default=None, ge=30, le=240)
    elevation_gain_m: float | None = Field(default=None, ge=0, le=20_000)


class ClimbingRoute(_Camel):
    grade: str = Field(min_length=1, max_length=12)
    attempts: int | None = Field(default=None, ge=1, le=100)
    sent: bool = True


class ClimbingMetrics(_Camel):
    kind: Literal["climbing"] = "climbing"
    style: ClimbingStyle = "boulder"
    routes: list[ClimbingRoute] = Field(default_factory=list, max_length=100)


class GenericMetrics(_Camel):
    kind: Literal["generic"] = "generic"
    notes: str | None = Field(default=None, max_length=500)


SessionMetrics = Annotated[
    CombatMetrics | EnduranceMetrics | ClimbingMetrics | GenericMetrics,
    Field(discriminator="kind"),
]
