import uuid
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics import periods
from app.analytics.discipline_seed import DISCIPLINE_SEED
from app.analytics.impacts import compute_discipline_impacts, compute_muscle_impacts
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import sessions
from app.crud.catalog import exercise_muscle_map
from app.crud.disciplines import load_catalog
from app.models import TrainingSession, User
from app.schemas.gym import GymSessionOut, MuscleImpactOut
from app.schemas.history import HighlightsOut, HistorySummaryOut, SessionPageOut
from app.schemas.session import (
    MuscleImpactOut as LegacyMuscleImpactOut,
)
from app.schemas.session import (
    SessionIn,
    SessionOut,
    SessionUpdateIn,
)
from app.schemas.watch import (
    ClassifyIn,
    ClassifyPreviewIn,
    ClassifyPreviewOut,
    PendingWatchListOut,
    PendingWatchOut,
)
from app.services import session_ingest, watch_classify

router = APIRouter(prefix="/sessions", tags=["sessions"])

SEED_NAMES = {code: name for name, code, *_ in DISCIPLINE_SEED}


@router.post(
    "", response_model=GymSessionOut | SessionOut, status_code=status.HTTP_201_CREATED
)
async def create_session(
    body: SessionIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    record = await session_ingest.create_session(
        session, current_user.id, body, weight_kg=current_user.weight_kg
    )
    reloaded = await sessions.get_for_user(session, record.id, current_user.id)
    assert reloaded is not None
    return await session_out(session, reloaded)


@router.get("", response_model=SessionPageOut)
async def list_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
    q: Annotated[str | None, Query(max_length=120)] = None,
    discipline: Annotated[list[str] | None, Query()] = None,
) -> SessionPageOut:
    items = await sessions.list_by_user(
        session,
        current_user.id,
        limit=page_size,
        offset=(page - 1) * page_size,
        q=q,
        disciplines=discipline,
    )
    total = await sessions.count_by_user(
        session, current_user.id, q=q, disciplines=discipline
    )
    return SessionPageOut(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
    )


@router.get("/summary", response_model=HistorySummaryOut)
async def sessions_summary(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 7,
) -> HistorySummaryOut:
    """Resumen del periodo (Capa 1): destacados, tiempo/kcal por actividad,
    progresion vs. periodo anterior y entrenos recientes."""
    now = datetime.now(UTC)
    start, end = periods.period_range(days, now)
    current = await sessions.list_in_range_light(session, current_user.id, start, end)
    prev_start, prev_end = periods.previous_period(start, end)
    previous = await sessions.list_in_range_light(
        session, current_user.id, prev_start, prev_end
    )
    recent = await sessions.list_recent_for_user(
        session, current_user.id, start=start, end=end, limit=5
    )
    return HistorySummaryOut(
        days=days,
        highlights=HighlightsOut(
            total_sessions=len(current),
            total_duration_minutes=sum(ts.duration_minutes or 0 for ts in current),
            total_volume_kg=round(sum(ts.volume_kg or 0 for ts in current), 1),
            total_kcal=round(sum(ts.estimated_kcal or 0 for ts in current), 1),
        ),
        by_discipline=periods.discipline_totals(current),
        deltas=periods.compute_discipline_deltas(current, previous),
        recent=recent,
    )


@router.get("/unclassified", response_model=PendingWatchListOut)
async def unclassified_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PendingWatchListOut:
    """Entrenos del reloj sin deporte concreto, pendientes de catalogar (ADR-012)."""
    items: list[PendingWatchOut] = []
    for record in await watch_classify.list_pending(session, current_user.id):
        activity = (record.details or {}).get("activity")
        info = activity if isinstance(activity, dict) else {}
        trimp = (record.details or {}).get("trimp")
        items.append(
            PendingWatchOut(
                id=record.id,
                performed_at=record.performed_at,
                duration_minutes=record.duration_minutes,
                estimated_kcal=record.estimated_kcal,
                avg_heart_rate=record.avg_heart_rate,
                max_heart_rate=record.max_heart_rate,
                distance_meters=record.distance_meters,
                sport=str(info["sport"]) if info.get("sport") else None,
                sub_sport=str(info["subSport"]) if info.get("subSport") else None,
                trimp=float(trimp) if isinstance(trimp, int | float) else None,
            )
        )
    return PendingWatchListOut(items=items)


@router.post("/classify/preview", response_model=ClassifyPreviewOut)
async def classify_preview(
    body: ClassifyPreviewIn,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ClassifyPreviewOut:
    """La IA interpreta la descripción del entreno; no guarda nada."""
    try:
        return await watch_classify.preview(body.text)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La IA no está disponible; elige la actividad a mano.",
        ) from exc


@router.post("/{session_id}/classify", response_model=GymSessionOut | SessionOut)
async def classify_session(
    session_id: uuid.UUID,
    body: ClassifyIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    """Asigna la actividad real a un entreno del reloj conservando FC, zonas y kcal."""
    info = (await load_catalog(session)).info(body.discipline)
    label = info.name if info else SEED_NAMES.get(body.discipline, body.discipline)
    try:
        await watch_classify.classify(
            session,
            current_user.id,
            session_id,
            body,
            weight_kg=current_user.weight_kg,
            label=label,
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from None
    except watch_classify.ClassifyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None
    reloaded = await sessions.get_for_user(session, session_id, current_user.id)
    assert reloaded is not None
    return await session_out(session, reloaded)


@router.post("/{session_id}/classify/skip", status_code=status.HTTP_204_NO_CONTENT)
async def skip_classification(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """«No catalogar»: no se vuelve a preguntar por este entreno."""
    try:
        await watch_classify.skip(session, current_user.id, session_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from None
    except watch_classify.ClassifyError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None


@router.get("/{session_id}", response_model=GymSessionOut | SessionOut)
async def get_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    record = await sessions.get_for_user(session, session_id, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return await session_out(session, record)


async def session_out(
    session: AsyncSession, record: TrainingSession
) -> GymSessionOut | SessionOut:
    catalog = await exercise_muscle_map(session)
    if record.workout_exercises:
        flat = gym_analytics.flatten_workout_exercises(record.workout_exercises)
        impacts = compute_muscle_impacts(flat, catalog)
        out_gym = GymSessionOut.model_validate(record)
        details = record.details or {}
        calories = details.get("calories")
        out_gym.calories = calories if isinstance(calories, (int, float)) else None
        out_gym.muscle_impacts = [
            MuscleImpactOut(
                muscle_group=item.muscle_group,
                activation=item.activation,
                zone=item.zone,
            )
            for item in impacts
        ]
        return out_gym
    impacts = compute_muscle_impacts(record.exercises, catalog)
    if not impacts:
        discipline_info = (await load_catalog(session)).info(record.discipline)
        impacts = compute_discipline_impacts(
            record.discipline,
            profile=discipline_info.profile if discipline_info else None,
        )
    out_legacy = SessionOut.model_validate(record)
    out_legacy.muscle_impacts = [
        LegacyMuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
        for item in impacts
    ]
    return out_legacy


@router.put("/{session_id}", response_model=GymSessionOut | SessionOut)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdateIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    record = await sessions.get_for_user(session, session_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    try:
        await sessions.update_for_user(session, record, body, weight_kg=current_user.weight_kg)
    except sessions.SessionUpdateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from None
    reloaded = await sessions.get_for_user(session, session_id, current_user.id)
    assert reloaded is not None
    return await session_out(session, reloaded)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await sessions.delete_for_user(session, session_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
