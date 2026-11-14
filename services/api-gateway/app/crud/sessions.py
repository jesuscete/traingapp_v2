import math
import uuid
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.analytics import kcal as kcal_analytics
from app.crud.disciplines import load_catalog
from app.models import Exercise, TrainingSession, WorkoutExercise, WorkoutSet
from app.schemas.metrics import CombatMetrics, EnduranceMetrics, WodMetrics
from app.schemas.session import SessionIn, SessionUpdateIn

_GYM_LOADS = (
    selectinload(TrainingSession.workout_exercises)
    .selectinload(WorkoutExercise.sets)
    .selectinload(WorkoutSet.entries),
    selectinload(TrainingSession.summary),
)


def _exercise_volume(exercise: Exercise) -> float:
    if exercise.sets and exercise.reps and exercise.weight_kg:
        return exercise.sets * exercise.reps * exercise.weight_kg
    return 0.0


exercise_volume = _exercise_volume


def _as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _estimate_kcal(
    data: SessionIn,
    weight_kg: float | None,
    *,
    kind: str | None = None,
    met_value: float | None = None,
) -> tuple[float | None, dict[str, object]]:
    minutes: float | None = data.duration_minutes
    if minutes is None:
        exercises_minutes = sum(ex.duration_minutes or 0 for ex in data.exercises)
        minutes = exercises_minutes or None

    details = dict(data.details or {})
    input_ = kcal_analytics.SessionKcalInput(
        discipline=data.discipline,
        weight_kg=weight_kg,
        duration_minutes=int(minutes) if minutes is not None else None,
        rpe=_as_int(details.get("rpe")) or data.intensity,
        avg_heart_rate=_as_float(details.get("avgHeartRate")),
        workout_type=_as_str(details.get("workoutType")),
        distance_meters=data.distance_meters,
        exercises=tuple(
            kcal_analytics.ExerciseInput(
                name=ex.name,
                weight_kg=ex.weight_kg,
                sets=ex.sets,
                reps=ex.reps,
                rest_seconds=_as_int((ex.details or {}).get("restSeconds")),
            )
            for ex in data.exercises
        ),
        kind=kind,
        met_value=met_value,
    )
    estimate = kcal_analytics.estimate(input_)
    details["kcal_confidence"] = estimate.confidence
    details["kcal_confidence_level"] = estimate.confidence_level
    details["kcal_factors"] = estimate.factors
    return estimate.kcal, details


def _with_metrics(data: SessionIn) -> SessionIn:
    """Vuelca las métricas en `details` y completa distancia y duración si faltan."""
    metrics = data.metrics
    if metrics is None:
        return data
    details = dict(data.details or {})
    details["metrics"] = metrics.model_dump(by_alias=True, exclude_none=True)
    update: dict[str, object] = {"details": details}
    if isinstance(metrics, EnduranceMetrics):
        if data.distance_meters is None and metrics.distance_meters is not None:
            update["distance_meters"] = metrics.distance_meters
        if metrics.avg_heart_rate is not None:
            details.setdefault("avgHeartRate", metrics.avg_heart_rate)
    if isinstance(metrics, CombatMetrics) and data.duration_minutes is None:
        update["duration_minutes"] = round(sum(b.total_minutes() for b in metrics.blocks))
    if isinstance(metrics, WodMetrics) and data.duration_minutes is None:
        seconds = metrics.time_seconds or sum(s.seconds for s in metrics.splits)
        minutes = seconds / 60 if seconds else metrics.time_cap_minutes
        if minutes:
            update["duration_minutes"] = max(1, math.ceil(minutes))
    return data.model_copy(update=update)


def _endurance_columns(data: SessionIn) -> dict[str, float | None]:
    metrics = data.metrics
    if not isinstance(metrics, EnduranceMetrics):
        return {}
    return {
        "avg_heart_rate": metrics.avg_heart_rate,
        "max_heart_rate": metrics.max_heart_rate,
        "elevation_gain_m": metrics.elevation_gain_m,
    }


async def create(
    session: AsyncSession,
    user_id: uuid.UUID,
    data: SessionIn,
    *,
    weight_kg: float | None = None,
) -> TrainingSession:
    data = _with_metrics(data)
    exercises = [
        Exercise(**exercise.model_dump(exclude_none=True))
        for exercise in data.exercises
    ]
    for exercise in exercises:
        exercise.volume_kg = _exercise_volume(exercise)

    discipline_info = (await load_catalog(session)).info(data.discipline)
    estimated_kcal, enriched_details = _estimate_kcal(
        data,
        weight_kg,
        kind=discipline_info.kind if discipline_info else None,
        met_value=discipline_info.met if discipline_info else None,
    )

    record = TrainingSession(
        user_id=user_id,
        discipline=data.discipline,
        raw_text=data.raw_text,
        performed_at=data.performed_at,
        duration_minutes=data.duration_minutes,
        distance_meters=data.distance_meters,
        intensity=data.intensity,
        fatigue=data.fatigue,
        note=data.note,
        routine_day_id=data.routine_day_id,
        details=enriched_details,
        estimated_kcal=estimated_kcal,
        volume_kg=sum(exercise.volume_kg for exercise in exercises),
        exercises=exercises,
        **_endurance_columns(data),
    )
    session.add(record)
    await session.commit()
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == record.id)
        .options(selectinload(TrainingSession.exercises))
    )
    return result.scalar_one()


def _filters(
    user_id: uuid.UUID,
    *,
    q: str | None = None,
    disciplines: list[str] | None = None,
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = [TrainingSession.user_id == user_id]
    if disciplines:
        conditions.append(TrainingSession.discipline.in_(disciplines))
    if q:
        pattern = f"%{q}%"
        conditions.append(
            or_(
                TrainingSession.raw_text.ilike(pattern),
                exists().where(
                    and_(
                        Exercise.session_id == TrainingSession.id,
                        Exercise.name.ilike(pattern),
                    )
                ),
                exists().where(
                    and_(
                        WorkoutExercise.session_id == TrainingSession.id,
                        WorkoutExercise.name.ilike(pattern),
                    )
                ),
            )
        )
    return conditions


async def count_by_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    q: str | None = None,
    disciplines: list[str] | None = None,
) -> int:
    filters = _filters(user_id, q=q, disciplines=disciplines)
    result = await session.execute(
        select(func.count()).select_from(TrainingSession).where(*filters)
    )
    return result.scalar_one()


async def list_by_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
    offset: int = 0,
    q: str | None = None,
    disciplines: list[str] | None = None,
) -> list[TrainingSession]:
    filters = _filters(user_id, q=q, disciplines=disciplines)
    result = await session.execute(
        select(TrainingSession)
        .where(*filters)
        .order_by(TrainingSession.performed_at.desc(), TrainingSession.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def list_recent_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    start: datetime,
    end: datetime,
    limit: int = 5,
) -> list[TrainingSession]:
    result = await session.execute(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.performed_at >= start,
            TrainingSession.performed_at < end,
        )
        .order_by(TrainingSession.performed_at.desc(), TrainingSession.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_in_range_light(
    session: AsyncSession,
    user_id: uuid.UUID,
    start: datetime,
    end: datetime | None = None,
) -> list[TrainingSession]:
    query = (
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.performed_at >= start,
        )
        .order_by(TrainingSession.performed_at)
    )
    if end is not None:
        query = query.where(TrainingSession.performed_at < end)
    result = await session.execute(query)
    return list(result.scalars().all())


async def legacy_strength_sessions(
    session: AsyncSession, disciplines: frozenset[str]
) -> list[TrainingSession]:
    """Sesiones de fuerza con ejercicios planos y sin modelo gym (ADR-001)."""
    result = await session.execute(
        select(TrainingSession)
        .where(
            TrainingSession.discipline.in_(disciplines),
            exists().where(Exercise.session_id == TrainingSession.id),
            ~exists().where(WorkoutExercise.session_id == TrainingSession.id),
        )
        .options(selectinload(TrainingSession.exercises))
    )
    return list(result.scalars().all())


async def get_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> TrainingSession | None:
    result = await session.execute(
        select(TrainingSession)
        .where(TrainingSession.id == session_id, TrainingSession.user_id == user_id)
        .options(selectinload(TrainingSession.exercises), *_GYM_LOADS)
    )
    return result.scalar_one_or_none()


class SessionUpdateError(Exception):
    """La edición no es válida para esta sesión."""


WATCH_KCAL_KEY = "watchKcal"
HEADER_FIELDS = ("raw_text", "performed_at", "duration_minutes", "intensity", "fatigue", "note")


async def update_for_user(
    session: AsyncSession,
    record: TrainingSession,
    data: SessionUpdateIn,
    *,
    weight_kg: float | None,
) -> None:
    """Aplica una edición parcial; en sesiones no-gym valida métricas y recalcula kcal."""
    sent = data.model_fields_set
    for field in HEADER_FIELDS:
        if field in sent:
            setattr(record, field, getattr(data, field))
    is_strength = record.discipline == "gym" or bool(record.workout_exercises)
    if "metrics" in sent and data.metrics is not None:
        if is_strength:
            raise SessionUpdateError("Las sesiones de gimnasio no admiten métricas")
        try:
            rebuilt = SessionIn.model_validate(
                {
                    "discipline": record.discipline,
                    "raw_text": record.raw_text,
                    "performed_at": record.performed_at,
                    "metrics": data.metrics,
                }
            )
        except ValidationError as exc:
            raise SessionUpdateError(exc.errors(include_url=False)[0]["msg"]) from exc
        normalized = _with_metrics(rebuilt.model_copy(update={"details": record.details}))
        record.details = normalized.details
        for column, value in _endurance_columns(normalized).items():
            setattr(record, column, value)
        if normalized.distance_meters is not None:
            record.distance_meters = normalized.distance_meters
        if record.duration_minutes is None and normalized.duration_minutes is not None:
            record.duration_minutes = normalized.duration_minutes
    if not is_strength:
        current = SessionIn.model_validate(
            {
                "discipline": record.discipline,
                "raw_text": record.raw_text,
                "performed_at": record.performed_at,
                "duration_minutes": record.duration_minutes,
                "distance_meters": record.distance_meters,
                "intensity": record.intensity,
                "details": record.details,
            }
        )
        info = (await load_catalog(session)).info(record.discipline)
        record.estimated_kcal, record.details = _estimate_kcal(
            current,
            weight_kg,
            kind=info.kind if info else None,
            met_value=info.met if info else None,
        )
        # Las kcal medidas por el reloj valen más que cualquier estimación.
        watch_kcal = _as_float((record.details or {}).get(WATCH_KCAL_KEY))
        if watch_kcal is not None:
            record.estimated_kcal = watch_kcal
    await session.commit()


async def delete_for_user(
    session: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    record = await get_for_user(session, session_id, user_id)
    if record is None:
        return False
    await session.delete(record)
    await session.commit()
    return True
