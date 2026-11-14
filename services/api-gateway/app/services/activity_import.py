"""Importación de actividades de reloj (M6.1): archivo -> sesión, métricas, zonas y series."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import heart_rate as hr_calc
from app.analytics.activity_file import (
    ActivityFileError,
    ParsedActivity,
    downsample,
    km_splits,
    parse_activity,
)
from app.crud import gym as gym_crud
from app.crud import sessions as sessions_crud
from app.models import ActivityStream, TrainingSession, User
from app.schemas.gym import GymSessionIn, SetEntryIn, WorkoutExerciseIn, WorkoutSetIn
from app.schemas.metrics import EnduranceMetrics, metrics_kind_for
from app.schemas.session import SessionIn
from app.services import watch_classify

EXTERNAL_SOURCE = "file"
MAX_FILE_BYTES = 15 * 1024 * 1024
OVERLAP_TOLERANCE = timedelta(minutes=10)

# Deporte del reloj (FIT/TCX/GPX) -> disciplina de la app.
SPORT_TO_DISCIPLINE: dict[str, str] = {
    "running": "running",
    "trail_running": "running",
    "treadmill_running": "running",
    "cycling": "cycling",
    "e_biking": "cycling",
    "biking": "cycling",
    "swimming": "swimming",
    "lap_swimming": "swimming",
    "open_water": "swimming",
    "boxing": "boxing",
    "mixed_martial_arts": "martial_arts",
    "martial_arts": "martial_arts",
    "rock_climbing": "climbing",
    "bouldering": "climbing",
    "alpine_skiing": "ski_snowboard",
    "cross_country_skiing": "ski_snowboard",
    "snowboarding": "ski_snowboard",
    "tennis": "tennis",
    "soccer": "football",
    "basketball": "basketball",
    "volleyball": "volleyball",
    "golf": "golf",
}
DISCIPLINE_LABELS = {
    "running": "Carrera",
    "cycling": "Ciclismo",
    "swimming": "Natación",
    "gym": "Fuerza",
    "other": "Actividad",
}


@dataclass
class ImportResult:
    filename: str
    status: str  # imported | duplicate | overlap | error
    message: str
    session_id: uuid.UUID | None = None
    discipline: str | None = None
    suggested_max_hr: int | None = None


def discipline_for(act: ParsedActivity) -> str:
    if act.strength_sets or act.sub_sport == "strength_training":
        return "gym"
    return SPORT_TO_DISCIPLINE.get(act.sub_sport or "", SPORT_TO_DISCIPLINE.get(act.sport, "other"))


def _age(user: User, on: datetime) -> int | None:
    return on.year - user.birth_year if user.birth_year else None


def _sex(user: User) -> hr_calc.Sex:
    return "male" if user.sex == "male" else "female" if user.sex == "female" else None


def activity_summary(act: ParsedActivity, user: User) -> dict[str, object]:
    """Zonas, TRIMP y parciales con el perfil de FC del usuario (estimado si falta)."""
    profile = hr_calc.hr_profile(user.max_hr, user.resting_hr, _age(user, act.start))
    times = [s.t for s in act.samples]
    hrs = [s.hr for s in act.samples]
    has_hr = any(h for h in hrs)
    return {
        "source": EXTERNAL_SOURCE,
        "sport": act.sport,
        "subSport": act.sub_sport,
        "avgHr": act.avg_hr,
        "maxHr": act.max_hr,
        "avgCadence": act.avg_cadence,
        "distanceM": act.distance_m,
        "durationS": act.duration_s,
        "ascentM": act.ascent_m,
        "deviceCalories": act.calories,
        "trimp": hr_calc.trimp(times, hrs, profile, _sex(user)) if has_hr else None,
        "zonesSeconds": hr_calc.time_in_zones(times, hrs, profile) if has_hr else None,
        "zoneBounds": hr_calc.zone_bounds(profile),
        "hrProfile": {
            "maxHr": profile.max_hr,
            "restingHr": profile.resting_hr,
            "maxEstimated": profile.max_estimated,
            "restingEstimated": profile.resting_estimated,
        },
        "kmSplits": km_splits(act.samples),
        "laps": len(act.laps),
    }


def _kcal(act: ParsedActivity, user: User) -> float | None:
    """Kcal del reloj (Garmin usa Firstbeat) > Keytel por FC > lo que estime kcal.py."""
    if act.calories:
        return act.calories
    age = _age(user, act.start)
    if act.avg_hr and user.weight_kg and age:
        return hr_calc.keytel_kcal(act.avg_hr, user.weight_kg, age, _sex(user), act.duration_s / 60)
    return None


STREAM_KEYS = ("t", "hr", "speed", "altitude", "cadence", "power", "distance", "lat", "lon")


async def _existing(
    session: AsyncSession, user_id: uuid.UUID, fingerprint: str, source: str = EXTERNAL_SOURCE
) -> TrainingSession | None:
    found: TrainingSession | None = await session.scalar(
        select(TrainingSession).where(
            TrainingSession.user_id == user_id,
            TrainingSession.external_source == source,
            TrainingSession.external_id == fingerprint,
        )
    )
    return found


async def _overlapping(
    session: AsyncSession, user_id: uuid.UUID, act: ParsedActivity, discipline: str
) -> TrainingSession | None:
    """Sesión registrada a mano a la misma hora y del mismo deporte (posible duplicado)."""
    start = act.start - OVERLAP_TOLERANCE
    end = act.start + timedelta(seconds=act.duration_s) + OVERLAP_TOLERANCE
    found: TrainingSession | None = await session.scalar(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.discipline == discipline,
            TrainingSession.performed_at >= start,
            TrainingSession.performed_at <= end,
        )
        .limit(1)
    )
    return found


def _gym_input(act: ParsedActivity) -> GymSessionIn:
    groups: list[tuple[str, list[WorkoutSetIn]]] = []
    for strength in act.strength_sets:
        name = (strength.exercise or "Ejercicio de fuerza").replace("_", " ").capitalize()
        if not groups or groups[-1][0] != name:
            groups.append((name, []))
        sets = groups[-1][1]
        sets.append(
            WorkoutSetIn(
                set_number=len(sets) + 1,
                entries=[SetEntryIn(entry_order=0, reps=strength.reps, weight=strength.weight_kg)],
            )
        )
    exercises = [
        WorkoutExerciseIn(name=name, order_index=i, sets=sets)
        for i, (name, sets) in enumerate(groups)
    ]
    if not exercises:
        exercises = [
            WorkoutExerciseIn(
                name="Sesión de fuerza",
                order_index=0,
                sets=[WorkoutSetIn(set_number=1, entries=[SetEntryIn(entry_order=0)])],
            )
        ]
    return GymSessionIn(
        raw_text="Fuerza (importada del reloj)",
        performed_at=act.start,
        duration_minutes=round(act.duration_s / 60),
        exercises=exercises,
    )


def _session_input(act: ParsedActivity, discipline: str, summary: dict[str, object]) -> SessionIn:
    label = DISCIPLINE_LABELS.get(discipline, discipline.capitalize())
    km = f" · {act.distance_m / 1000:.1f} km" if act.distance_m else ""
    metrics = None
    if metrics_kind_for(discipline) == "endurance":
        metrics = EnduranceMetrics(
            distance_meters=act.distance_m or None,
            avg_heart_rate=round(act.avg_hr) if act.avg_hr else None,
            max_heart_rate=round(act.max_hr) if act.max_hr else None,
            elevation_gain_m=act.ascent_m,
        )
    return SessionIn.model_validate(
        {
            "discipline": discipline,
            "raw_text": f"{label}{km} (importada del reloj)",
            "performed_at": act.start,
            "duration_minutes": round(act.duration_s / 60),
            "distance_meters": act.distance_m,
            "details": {"activity": summary, "trimp": summary.get("trimp")},
            "metrics": metrics,
        }
    )


async def import_file(
    session: AsyncSession,
    user: User,
    filename: str,
    data: bytes,
    *,
    force: bool = False,
    source: str = EXTERNAL_SOURCE,
    external_id: str | None = None,
) -> ImportResult:
    if len(data) > MAX_FILE_BYTES:
        return ImportResult(filename, "error", "Archivo demasiado grande (máx. 15 MB)")
    try:
        act = parse_activity(filename, data)
    except ActivityFileError as exc:
        return ImportResult(filename, "error", str(exc))

    discipline = discipline_for(act)
    duplicate = await _existing(session, user.id, act.fingerprint)
    if duplicate is None and external_id is not None:
        duplicate = await _existing(session, user.id, external_id, source)
    if duplicate is not None:
        return ImportResult(filename, "duplicate", "Ya estaba importada", duplicate.id, discipline)
    if not force:
        overlap = await _overlapping(session, user.id, act, discipline)
        if overlap is not None:
            return ImportResult(
                filename,
                "overlap",
                "Ya hay una sesión de ese deporte a esa hora. Importa con 'forzar' si es otra.",
                overlap.id,
                discipline,
            )

    summary = {**activity_summary(act, user), "source": source}
    if discipline == "gym":
        record = await gym_crud.create_gym(
            session, user.id, _gym_input(act), weight_kg=user.weight_kg
        )
    else:
        record = await sessions_crud.create(
            session, user.id, _session_input(act, discipline, summary), weight_kg=user.weight_kg
        )
        record.details = {**(record.details or {}), "activity": summary, "trimp": summary["trimp"]}
    record.external_source = source
    record.external_id = external_id or act.fingerprint
    kcal = _kcal(act, user)
    if kcal is not None:
        record.estimated_kcal = round(kcal, 1)
        record.details = {
            **(record.details or {}),
            sessions_crud.WATCH_KCAL_KEY: record.estimated_kcal,
        }
    watch_classify.mark_if_unspecific(record)
    if act.avg_hr:
        record.avg_heart_rate = act.avg_hr
    if act.max_hr:
        record.max_heart_rate = act.max_hr
    samples = downsample(act.samples)
    session.add(
        ActivityStream(
            session_id=record.id,
            samples={
                key: [getattr(s, key) for s in samples]
                for key in STREAM_KEYS
                if any(getattr(s, key) is not None for s in samples)
            },
            laps=[lap.__dict__ for lap in act.laps],
        )
    )
    await session.commit()

    suggested = None
    profile = summary["hrProfile"]
    if act.max_hr and isinstance(profile, dict) and act.max_hr > float(str(profile["maxHr"])):
        suggested = round(act.max_hr)
    label = DISCIPLINE_LABELS.get(discipline, discipline)
    return ImportResult(
        filename, "imported", f"{label} importada", record.id, discipline, suggested
    )


async def activity_detail(
    session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> tuple[TrainingSession, ActivityStream | None] | None:
    record = await session.scalar(
        select(TrainingSession).where(
            TrainingSession.id == session_id, TrainingSession.user_id == user_id
        )
    )
    if record is None:
        return None
    stream = await session.get(ActivityStream, session_id)
    return record, stream
