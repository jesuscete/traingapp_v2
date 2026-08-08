from datetime import date

from pydantic import Field

from app.schemas.session import CamelModel


class DisciplineTotalOut(CamelModel):
    discipline: str
    sessions: int
    volume_kg: float
    duration_minutes: int


class WeeklyVolumeOut(CamelModel):
    start: date
    sessions: int
    volume_kg: float


class OverviewOut(CamelModel):
    period_days: int
    total_sessions: int
    total_volume_kg: float
    total_duration_minutes: int
    sessions_per_week: float
    by_discipline: list[DisciplineTotalOut]
    weekly_volume: list[WeeklyVolumeOut]


class TopExerciseOut(CamelModel):
    name: str
    volume_kg: float
    sets: int


class MuscleGroupVolumeOut(CamelModel):
    muscle_group: str
    volume_kg: float
    sessions: int
    top_exercises: list[TopExerciseOut]


class ExerciseProgressOut(CamelModel):
    exercise: str
    best_1rm: float | None
    first_1rm: float | None
    delta_pct: float | None
    sessions: int


class VolumeOut(CamelModel):
    period_days: int
    total_volume_kg: float
    unclassified_volume_kg: float
    by_muscle_group: list[MuscleGroupVolumeOut]
    exercise_progress: list[ExerciseProgressOut]


class CardioDisciplineOut(CamelModel):
    discipline: str
    sessions: int
    duration_minutes: int
    distance_meters: float | None
    avg_duration_minutes: float


class CardioOut(CamelModel):
    period_days: int
    total_duration_minutes: int
    total_distance_meters: float | None
    by_discipline: list[CardioDisciplineOut]


class PeriodTotalsOut(CamelModel):
    sessions: int
    volume_kg: float
    duration_minutes: int


class InsightOut(CamelModel):
    kind: str
    severity: str
    message: str


class ProgressOut(CamelModel):
    period_days: int
    current: PeriodTotalsOut
    previous: PeriodTotalsOut
    volume_delta_pct: float | None
    session_delta_pct: float | None
    insights: list[InsightOut]


class EnergyOut(CamelModel):
    weight_kg: float | None
    height_cm: float | None
    age: int | None
    goal: str | None
    bmr_kcal: float | None
    tdee_kcal: float | None
    target_kcal: float | None


class FatigueMuscleOut(CamelModel):
    muscle_group: str
    fatigue: float
    impulse_today: float
    level: str
    acwr: float


class FatigueRiskOut(CamelModel):
    muscle_group: str
    level: str
    reasons: list[str]


class ReadinessOut(CamelModel):
    date: date
    sleep_hours: float | None
    doms: int | None
    rest_day: bool
    hrv_score: float | None = None
    resting_hr: float | None = None


class ReadinessIn(CamelModel):
    date: date
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    doms: int | None = Field(default=None, ge=1, le=10)
    rest_day: bool = False
    hrv_score: float | None = Field(default=None, ge=0, le=1)
    resting_hr: float | None = Field(default=None, ge=25, le=220)


class DomsEntryIn(CamelModel):
    muscle_group: str = Field(min_length=1, max_length=40)
    pain: int = Field(ge=0, le=10)


class DomsIn(CamelModel):
    date: date
    entries: list[DomsEntryIn] = Field(default_factory=list)


class DomsEntryOut(CamelModel):
    muscle_group: str
    pain: int


class DomsOut(CamelModel):
    date: date
    entries: list[DomsEntryOut]


class FatigueOut(CamelModel):
    as_of: date
    projected: date
    muscles: list[FatigueMuscleOut]
    max_fatigue: float
    avg_fatigue: float
    readiness: ReadinessOut | None
    risks: list[FatigueRiskOut]
