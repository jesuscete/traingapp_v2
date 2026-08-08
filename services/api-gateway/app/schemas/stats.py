from datetime import date

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
