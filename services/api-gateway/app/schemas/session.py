import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

from app.analytics.catalog_seed import zone_of
from app.schemas.metrics import SessionMetrics, metrics_kind_for

# Enum de disciplinas del catalogo canonical (`discipline_seed.DISCIPLINE_SEED`).
# Mantener sincronizado con la semilla: no hay validacion dinamica en schemas.
Discipline = Literal[
    "gym",
    "calisthenics",
    "boxing",
    "martial_arts",
    "running",
    "cycling",
    "swimming",
    "climbing",
    "football",
    "basketball",
    "volleyball",
    "cricket",
    "baseball",
    "hockey",
    "rugby",
    "handball",
    "badminton",
    "table_tennis",
    "tennis",
    "ski_snowboard",
    "golf",
    "other",
]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class ExerciseIn(CamelModel):
    name: str = Field(min_length=1, max_length=120)
    sets: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=1)
    weight_kg: float | None = Field(default=None, ge=0)
    duration_minutes: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    details: dict[str, object] | None = None


class ExerciseOut(CamelModel):
    id: uuid.UUID
    name: str
    sets: int | None
    reps: int | None
    weight_kg: float | None
    duration_minutes: float | None
    distance_meters: float | None
    volume_kg: float
    details: dict[str, object] | None = None


class SessionIn(CamelModel):
    discipline: Discipline
    raw_text: str = Field(min_length=1)
    performed_at: datetime
    duration_minutes: int | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    note: str | None = None
    routine_day_id: uuid.UUID | None = None
    details: dict[str, object] | None = None
    metrics: SessionMetrics | None = None
    exercises: list[ExerciseIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _metrics_match_discipline(self) -> "SessionIn":
        if self.metrics is None:
            return self
        if self.discipline == "gym":
            raise ValueError("Las sesiones de gimnasio usan series, no métricas")
        expected = metrics_kind_for(self.discipline)
        if self.metrics.kind not in (expected, "generic"):
            raise ValueError(
                f"Métricas '{self.metrics.kind}' no válidas para {self.discipline} "
                f"(se esperan '{expected}')"
            )
        return self


class SessionUpdateIn(CamelModel):
    """Edición parcial: solo se aplican los campos enviados."""

    raw_text: str | None = Field(default=None, min_length=1)
    performed_at: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=0)
    intensity: int | None = Field(default=None, ge=1, le=10)
    fatigue: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=2000)
    metrics: SessionMetrics | None = None


class MuscleImpactOut(CamelModel):
    muscle_group: str
    activation: float
    zone: str = "other"

    @model_validator(mode="after")
    def _derive_zone(self) -> "MuscleImpactOut":
        # Sin zona explícita se deduce del grupo (antes caía todo en "otros").
        if self.zone == "other":
            self.zone = zone_of(self.muscle_group)
        return self


class SessionOut(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    distance_meters: float | None = None
    volume_kg: float
    estimated_kcal: float | None = None
    intensity: int | None = None
    fatigue: int | None = None
    note: str | None
    details: dict[str, object] | None = None
    created_at: datetime
    exercises: list[ExerciseOut]
    muscle_impacts: list[MuscleImpactOut] = Field(default_factory=list)


class SessionListItem(CamelModel):
    id: uuid.UUID
    discipline: str
    raw_text: str
    performed_at: datetime
    duration_minutes: int | None
    volume_kg: float
    estimated_kcal: float | None = None
    intensity: int | None = None
    fatigue: int | None = None
