"""Entrenos del reloj sin catalogar (ADR-012).

Garmin manda muchas sesiones como «Cardio» / «Entreno» genérico. Al importarlas quedan
pendientes; el usuario les asigna la actividad real (HYROX, boxeo, fútbol…) a mano o
describiéndola para que la IA la interprete, o decide no catalogarlas. La FC, zonas, TRIMP
y kcal del reloj se conservan; cambia la disciplina, y con ella la fatiga y el análisis.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.parser import fetch_draft
from app.crud import sessions as sessions_crud
from app.models import Exercise, TrainingSession
from app.schemas.chat import WorkoutDraftOut
from app.schemas.session import Discipline, ExerciseIn, SessionUpdateIn
from app.schemas.watch import ClassifyIn, ClassifyPreviewOut

Status = Literal["pending", "done", "skipped"]

# Disciplinas de importación que no dicen qué deporte fue.
UNSPECIFIC_DISCIPLINES = frozenset({"other"})
PENDING_WINDOW_DAYS = 60
WATCH_KCAL_KEY = sessions_crud.WATCH_KCAL_KEY
VALID_DISCIPLINES: frozenset[str] = frozenset(Discipline.__args__)  # type: ignore[attr-defined]


class ClassifyError(Exception):
    pass


def classification_of(record: TrainingSession) -> Status | None:
    info = (record.details or {}).get("classification")
    if isinstance(info, dict) and info.get("status") in ("pending", "done", "skipped"):
        return cast(Status, info["status"])
    return None


def _set_status(record: TrainingSession, status: Status) -> None:
    record.details = {
        **(record.details or {}),
        "classification": {"status": status, "at": datetime.now(UTC).isoformat()},
    }


def mark_if_unspecific(record: TrainingSession) -> None:
    """Al importar: si el reloj no dice el deporte, queda pendiente de catalogar."""
    if record.discipline in UNSPECIFIC_DISCIPLINES:
        _set_status(record, "pending")


async def list_pending(session: AsyncSession, user_id: uuid.UUID) -> list[TrainingSession]:
    since = datetime.now(UTC) - timedelta(days=PENDING_WINDOW_DAYS)
    rows = await session.scalars(
        select(TrainingSession)
        .where(
            TrainingSession.user_id == user_id,
            TrainingSession.external_source.is_not(None),
            TrainingSession.performed_at >= since,
        )
        .order_by(TrainingSession.performed_at.desc())
    )
    return [r for r in rows.all() if classification_of(r) == "pending"]


async def preview(text: str) -> ClassifyPreviewOut:
    """La IA interpreta la descripción («hice un HYROX de 4 estaciones…»); nada se guarda."""
    draft = WorkoutDraftOut.model_validate(await fetch_draft(text))
    discipline = draft.discipline if draft.discipline in VALID_DISCIPLINES else None
    return ClassifyPreviewOut(
        discipline=cast(Discipline | None, discipline),
        exercises=[
            ExerciseIn(
                name=e.name[:120],
                sets=e.sets if e.sets and e.sets >= 1 else None,
                reps=e.reps if e.reps and e.reps >= 1 else None,
                weight_kg=e.weight_kg if e.weight_kg and e.weight_kg >= 0 else None,
            )
            for e in draft.exercises
            if e.name.strip()
        ],
        metrics=draft.metrics,
        intensity=round(draft.suggested_rpe) if draft.suggested_rpe else None,
        unresolved=draft.unresolved,
    )


def _watch_raw_text(label: str, record: TrainingSession) -> str:
    km = f" · {record.distance_meters / 1000:.1f} km" if record.distance_meters else ""
    return f"{label}{km} (importada del reloj)"


async def _load(
    session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID
) -> TrainingSession:
    record = await sessions_crud.get_for_user(session, session_id, user_id)
    if record is None:
        raise LookupError("Session not found")
    if record.external_source is None:
        raise ClassifyError("Solo se pueden catalogar los entrenos importados del reloj")
    return record


async def classify(
    session: AsyncSession,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    body: ClassifyIn,
    *,
    weight_kg: float | None,
    label: str,
) -> TrainingSession:
    record = await _load(session, user_id, session_id)
    if record.discipline == "gym":
        raise ClassifyError("Las sesiones de fuerza del reloj ya están catalogadas")
    record.discipline = body.discipline
    if body.exercises is not None:
        record.exercises.clear()
        for ex in body.exercises:
            row = Exercise(**ex.model_dump(exclude_none=True))
            row.volume_kg = sessions_crud.exercise_volume(row)
            record.exercises.append(row)
        record.volume_kg = sum(e.volume_kg for e in record.exercises)
    _set_status(record, "done")
    update: dict[str, object] = {"raw_text": _watch_raw_text(label, record)}
    if body.note is not None:
        update["note"] = body.note
    if body.intensity is not None:
        update["intensity"] = body.intensity
    if body.metrics is not None:
        update["metrics"] = body.metrics
    try:
        await sessions_crud.update_for_user(
            session, record, SessionUpdateIn.model_validate(update), weight_kg=weight_kg
        )
    except sessions_crud.SessionUpdateError as exc:
        raise ClassifyError(str(exc)) from exc
    return record


async def skip(session: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
    """«No catalogar»: se queda genérico (análisis más impreciso) y no se vuelve a preguntar."""
    record = await _load(session, user_id, session_id)
    _set_status(record, "skipped")
    await session.commit()
