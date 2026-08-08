import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.analytics import catalog
from app.models import TrainingSession

CARDIO_DISCIPLINES = frozenset({"running", "cycling", "swimming", "boxing"})


def est_1rm(weight_kg: float | None, reps: int | None) -> float | None:
    if weight_kg is None or reps is None or reps < 1:
        return None
    if reps == 1:
        return weight_kg
    return weight_kg * (1 + reps / 30)


def _week_start(day: datetime) -> date:
    return day.date() - timedelta(days=day.weekday())


@dataclass
class DisciplineTotal:
    discipline: str
    sessions: int
    volume_kg: float
    duration_minutes: int


@dataclass
class WeeklyVolume:
    start: date
    sessions: int
    volume_kg: float


@dataclass
class OverviewResult:
    total_sessions: int
    total_volume_kg: float
    total_duration_minutes: int
    sessions_per_week: float
    by_discipline: list[DisciplineTotal]
    weekly_volume: list[WeeklyVolume]


@dataclass
class TopExercise:
    name: str
    volume_kg: float
    sets: int


@dataclass
class MuscleGroupVolume:
    muscle_group: str
    volume_kg: float
    sessions: int
    top_exercises: list[TopExercise]


@dataclass
class ExerciseProgress:
    exercise: str
    best_1rm: float | None
    first_1rm: float | None
    delta_pct: float | None
    sessions: int


@dataclass
class VolumeResult:
    total_volume_kg: float
    unclassified_volume_kg: float
    by_muscle_group: list[MuscleGroupVolume]
    exercise_progress: list[ExerciseProgress]


@dataclass
class CardioDiscipline:
    discipline: str
    sessions: int
    duration_minutes: int
    distance_meters: float | None
    avg_duration_minutes: float


@dataclass
class CardioResult:
    total_duration_minutes: int
    total_distance_meters: float | None
    by_discipline: list[CardioDiscipline]


@dataclass
class PeriodTotals:
    sessions: int
    volume_kg: float
    duration_minutes: int


@dataclass
class Insight:
    kind: str
    severity: str
    message: str


@dataclass
class ProgressResult:
    current: PeriodTotals
    previous: PeriodTotals
    volume_delta_pct: float | None
    session_delta_pct: float | None
    insights: list[Insight]


def _discipline_totals(sessions: list[TrainingSession]) -> list[DisciplineTotal]:
    sessions_count: dict[str, int] = defaultdict(int)
    volume: dict[str, float] = defaultdict(float)
    duration: dict[str, int] = defaultdict(int)
    for ts in sessions:
        sessions_count[ts.discipline] += 1
        volume[ts.discipline] += ts.volume_kg or 0
        duration[ts.discipline] += ts.duration_minutes or 0
    return [
        DisciplineTotal(
            discipline=name,
            sessions=sessions_count[name],
            volume_kg=volume[name],
            duration_minutes=duration[name],
        )
        for name in sorted(sessions_count)
    ]


def _weekly_volumes(sessions: list[TrainingSession]) -> list[WeeklyVolume]:
    sessions_count: dict[date, int] = defaultdict(int)
    volume: dict[date, float] = defaultdict(float)
    for ts in sessions:
        week = _week_start(ts.performed_at)
        sessions_count[week] += 1
        volume[week] += ts.volume_kg or 0
    return [
        WeeklyVolume(
            start=week,
            sessions=sessions_count[week],
            volume_kg=volume[week],
        )
        for week in sorted(sessions_count)
    ]


def compute_overview(sessions: list[TrainingSession], days: int) -> OverviewResult:
    total_sessions = len(sessions)
    total_volume = sum(ts.volume_kg or 0 for ts in sessions)
    total_duration = sum(ts.duration_minutes or 0 for ts in sessions)
    weeks = max(1, round(days / 7))
    return OverviewResult(
        total_sessions=total_sessions,
        total_volume_kg=total_volume,
        total_duration_minutes=total_duration,
        sessions_per_week=total_sessions / weeks,
        by_discipline=_discipline_totals(sessions),
        weekly_volume=_weekly_volumes(sessions),
    )


def compute_volume(sessions: list[TrainingSession]) -> VolumeResult:
    group_volume: dict[str, float] = defaultdict(float)
    group_sessions: dict[str, set[uuid.UUID]] = defaultdict(set)
    group_exercises: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    progress: dict[str, list[tuple[datetime, float]]] = defaultdict(list)
    unclassified = 0.0

    for ts in sessions:
        for exercise in ts.exercises:
            volume = exercise.volume_kg or 0.0
            group = catalog.muscle_group_of(exercise.name)
            if group is None:
                unclassified += volume
            else:
                group_volume[group] += volume
                group_sessions[group].add(ts.id)
                group_exercises[group][exercise.name.strip()].append(volume)
            one_rm = est_1rm(exercise.weight_kg, exercise.reps)
            if one_rm is not None:
                progress[catalog.normalize_exercise_name(exercise.name)].append(
                    (ts.performed_at, one_rm)
                )

    by_group: list[MuscleGroupVolume] = []
    for group in sorted(group_volume, key=lambda g: group_volume[g], reverse=True):
        per_exercise = group_exercises[group]
        top = sorted(
            (
                TopExercise(
                    name=name,
                    volume_kg=sum(volumes),
                    sets=0,
                )
                for name, volumes in per_exercise.items()
            ),
            key=lambda item: item.volume_kg,
            reverse=True,
        )[:3]
        by_group.append(
            MuscleGroupVolume(
                muscle_group=group,
                volume_kg=group_volume[group],
                sessions=len(group_sessions[group]),
                top_exercises=top,
            )
        )

    exercise_progress: list[ExerciseProgress] = []
    for name, measurements in progress.items():
        measurements.sort(key=lambda item: item[0])
        values = [value for _, value in measurements]
        best = max(values)
        first = values[0]
        delta = (best - first) / first * 100 if first > 0 else None
        exercise_progress.append(
            ExerciseProgress(
                exercise=name,
                best_1rm=best,
                first_1rm=first,
                delta_pct=delta,
                sessions=len(measurements),
            )
        )

    exercise_progress.sort(key=lambda item: item.sessions, reverse=True)
    return VolumeResult(
        total_volume_kg=sum(group_volume.values()) + unclassified,
        unclassified_volume_kg=unclassified,
        by_muscle_group=by_group,
        exercise_progress=exercise_progress,
    )


def compute_cardio(sessions: list[TrainingSession]) -> CardioResult:
    cardio = [ts for ts in sessions if ts.discipline in CARDIO_DISCIPLINES]
    sessions_count: dict[str, int] = defaultdict(int)
    duration: dict[str, int] = defaultdict(int)
    distance: dict[str, float] = defaultdict(float)
    for ts in cardio:
        sessions_count[ts.discipline] += 1
        duration[ts.discipline] += ts.duration_minutes or 0
        if ts.distance_meters:
            distance[ts.discipline] += ts.distance_meters

    result: list[CardioDiscipline] = []
    total_distance: float | None = 0.0
    for name in sorted(sessions_count):
        count = sessions_count[name]
        total_duration = duration[name]
        total_distance_value = distance[name]
        avg = round(total_duration / count, 1) if count else 0.0
        result.append(
            CardioDiscipline(
                discipline=name,
                sessions=count,
                duration_minutes=total_duration,
                distance_meters=total_distance_value if total_distance_value > 0 else None,
                avg_duration_minutes=avg,
            )
        )
        if total_distance is not None:
            total_distance += total_distance_value

    if not result:
        total_distance = None
    return CardioResult(
        total_duration_minutes=sum(item.duration_minutes for item in result),
        total_distance_meters=total_distance,
        by_discipline=result,
    )


def _period_totals(sessions: list[TrainingSession]) -> PeriodTotals:
    return PeriodTotals(
        sessions=len(sessions),
        volume_kg=sum(ts.volume_kg or 0 for ts in sessions),
        duration_minutes=sum(ts.duration_minutes or 0 for ts in sessions),
    )


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def compute_progress(
    current: list[TrainingSession], previous: list[TrainingSession]
) -> ProgressResult:
    current_totals = _period_totals(current)
    previous_totals = _period_totals(previous)
    volume = compute_volume(current)
    insights: list[Insight] = []

    if current_totals.sessions == 0:
        insights.append(
            Insight(
                kind="low_volume",
                severity="warning",
                message="No se registraron entrenamientos en el periodo actual.",
            )
        )

    for item in volume.exercise_progress:
        if (
            item.sessions >= 3
            and item.best_1rm is not None
            and item.first_1rm is not None
            and item.best_1rm == item.first_1rm
        ):
            insights.append(
                Insight(
                    kind="plateau",
                    severity="warning",
                    message=f"{item.exercise}: sin mejora de 1RM estimado en el periodo "
                    f"({item.sessions} entrenamientos).",
                )
            )
            break

    weeks = _weekly_volumes(current)
    if len(weeks) >= 2:
        last_volume = weeks[-1].volume_kg
        previous_mean = sum(week.volume_kg for week in weeks[:-1]) / (len(weeks) - 1)
        if previous_mean > 0 and last_volume > 1.5 * previous_mean:
            insights.append(
                Insight(
                    kind="overload",
                    severity="warning",
                    message=f"La última semana ({last_volume:.0f} kg) supera un 50% "
                    f"la media semanal anterior ({previous_mean:.0f} kg).",
                )
            )

    groups = [group.volume_kg for group in volume.by_muscle_group if group.volume_kg > 0]
    if len(groups) >= 2 and groups[0] > 1.4 * groups[1]:
        top = volume.by_muscle_group[0]
        second = volume.by_muscle_group[1]
        insights.append(
            Insight(
                kind="unbalance",
                severity="info",
                message=f"Desequilibrio: {top.muscle_group} ({top.volume_kg:.0f} kg) "
                f"frente a {second.muscle_group} ({second.volume_kg:.0f} kg).",
            )
        )

    return ProgressResult(
        current=current_totals,
        previous=previous_totals,
        volume_delta_pct=_pct_change(
            current_totals.volume_kg, previous_totals.volume_kg
        ),
        session_delta_pct=_pct_change(
            float(current_totals.sessions), float(previous_totals.sessions)
        ),
        insights=insights,
    )
