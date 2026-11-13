"""Métricas específicas por tipo de deporte (RF-01), guardadas en `details["metrics"]`.

Unión discriminada por `kind`. La fuerza no usa este esquema: va al modelo gym
(ADR-001).
"""

import uuid
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

MetricsKind = Literal["combat", "endurance", "climbing", "wod", "generic"]

# Disciplina -> tipo de métricas esperado. Lo que no aparece usa "generic".
DISCIPLINE_METRICS: dict[str, MetricsKind] = {
    "boxing": "combat",
    "martial_arts": "combat",
    "running": "endurance",
    "cycling": "endurance",
    "swimming": "endurance",
    "ski_snowboard": "endurance",
    "climbing": "climbing",
    "crossfit": "wod",
    "hyrox": "wod",
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


# For Time (rondas fijas, chipper, escalera), AMRAP, EMOM, Tabata, intervalos, fuerza,
# simulación HYROX y carrera HYROX oficial.
WodFormat = Literal[
    "for_time", "amrap", "emom", "tabata", "intervals", "strength", "hyrox_sim", "hyrox_race",
    "other",
]
HyroxCategory = Literal["open_men", "open_women", "pro_men", "pro_women", "doubles", "relay"]
MAX_WOD_SECONDS = 6 * 3600


class WodMovement(_Camel):
    """Un movimiento del WOD tal como se prescribe (por ronda o total)."""

    exercise_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    reps: int | None = Field(default=None, ge=1, le=10_000)
    weight_kg: float | None = Field(default=None, gt=0, le=500)
    distance_m: float | None = Field(default=None, gt=0, le=100_000)
    calories: int | None = Field(default=None, ge=1, le=5_000)


class WodSplit(_Camel):
    """Tramo cronometrado (HYROX: cada km y cada estación)."""

    name: str = Field(min_length=1, max_length=60)
    seconds: int = Field(ge=1, le=MAX_WOD_SECONDS)


class WodMetrics(_Camel):
    """WOD de CrossFit/HYROX apuntado al terminar: formato, puntuación y movimientos."""

    kind: Literal["wod"] = "wod"
    format: WodFormat = "for_time"
    name: str | None = Field(default=None, max_length=80)  # "Fran", "Murph"...
    scheme: str | None = Field(default=None, max_length=60)  # "21-15-9", "5 rondas"
    time_cap_minutes: float | None = Field(default=None, gt=0, le=360)
    # Puntuación (según formato): tiempo, rondas + reps, reps totales o carga.
    time_seconds: int | None = Field(default=None, ge=1, le=MAX_WOD_SECONDS)
    rounds: int | None = Field(default=None, ge=0, le=1_000)
    extra_reps: int | None = Field(default=None, ge=0, le=10_000)
    total_reps: int | None = Field(default=None, ge=0, le=100_000)
    load_kg: float | None = Field(default=None, gt=0, le=500)
    rx: bool = True
    hyrox_category: HyroxCategory | None = None
    movements: list[WodMovement] = Field(default_factory=list, max_length=30)
    splits: list[WodSplit] = Field(default_factory=list, max_length=40)

    def score_text(self) -> str | None:
        """Resultado legible para el resumen de la sesión."""
        if self.time_seconds is not None:
            minutes, seconds = divmod(self.time_seconds, 60)
            return f"{minutes}:{seconds:02d}"
        if self.rounds is not None:
            return f"{self.rounds} rondas" + (f" + {self.extra_reps}" if self.extra_reps else "")
        if self.total_reps is not None:
            return f"{self.total_reps} reps"
        if self.load_kg is not None:
            return f"{self.load_kg:g} kg"
        return None


class GenericMetrics(_Camel):
    kind: Literal["generic"] = "generic"
    notes: str | None = Field(default=None, max_length=500)


SessionMetrics = Annotated[
    CombatMetrics | EnduranceMetrics | ClimbingMetrics | WodMetrics | GenericMetrics,
    Field(discriminator="kind"),
]
