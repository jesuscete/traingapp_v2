import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import fatigue as fatigue_analytics
from app.models.fatigue import (
    DailyMuscleDoms,
    DailyReadiness,
    DisciplineMuscleLoad,
    UserMuscleCalibration,
)


async def load_map(
    session: AsyncSession,
) -> dict[str, dict[str, float]]:
    """Ponderaciones por disciplina desde el catalogo (fallback: defaults)."""
    result = await session.execute(
        select(DisciplineMuscleLoad).options(
            selectinload(DisciplineMuscleLoad.discipline)
        )
    )
    rows = list(result.scalars().all())
    if not rows:
        return dict(fatigue_analytics.MUSCLE_LOAD_DEFAULT)
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        if row.discipline is None:
            continue
        grouped.setdefault(row.discipline.normalized_name, {})[
            row.muscle_group
        ] = row.load
    return grouped


async def get_readiness(
    session: AsyncSession, user_id: uuid.UUID, day: date
) -> DailyReadiness | None:
    result = await session.execute(
        select(DailyReadiness).where(
            DailyReadiness.user_id == user_id, DailyReadiness.date == day
        )
    )
    return result.scalar_one_or_none()


async def readiness_since(
    session: AsyncSession, user_id: uuid.UUID, start: date
) -> list[DailyReadiness]:
    result = await session.execute(
        select(DailyReadiness)
        .where(DailyReadiness.user_id == user_id, DailyReadiness.date >= start)
        .order_by(DailyReadiness.date)
    )
    return list(result.scalars().all())


async def upsert_readiness(
    session: AsyncSession,
    user_id: uuid.UUID,
    day: date,
    *,
    sleep_hours: float | None = None,
    doms: int | None = None,
    rest_day: bool = False,
    hrv_score: float | None = None,
    resting_hr: float | None = None,
) -> DailyReadiness:
    record = await get_readiness(session, user_id, day)
    if record is None:
        record = DailyReadiness(
            user_id=user_id,
            date=day,
            sleep_hours=sleep_hours,
            doms=doms,
            rest_day=rest_day,
            hrv_score=hrv_score,
            resting_hr=resting_hr,
        )
        session.add(record)
    else:
        if sleep_hours is not None:
            record.sleep_hours = sleep_hours
        if doms is not None:
            record.doms = doms
        if hrv_score is not None:
            record.hrv_score = hrv_score
        if resting_hr is not None:
            record.resting_hr = resting_hr
        record.rest_day = rest_day
    await session.commit()
    await session.refresh(record)
    return record


async def get_doms(
    session: AsyncSession, user_id: uuid.UUID, day: date
) -> list[DailyMuscleDoms]:
    result = await session.execute(
        select(DailyMuscleDoms)
        .where(DailyMuscleDoms.user_id == user_id, DailyMuscleDoms.date == day)
        .order_by(DailyMuscleDoms.muscle_group)
    )
    return list(result.scalars().all())


async def doms_map(
    session: AsyncSession, user_id: uuid.UUID, start: date
) -> dict[date, dict[str, int]]:
    """Mapa date -> {muscle_group: pain} para el periodo (alimenta la fatiga)."""
    result = await session.execute(
        select(DailyMuscleDoms).where(
            DailyMuscleDoms.user_id == user_id, DailyMuscleDoms.date >= start
        )
    )
    grouped: dict[date, dict[str, int]] = {}
    for row in result.scalars().all():
        grouped.setdefault(row.date, {})[row.muscle_group] = row.pain
    return grouped


async def upsert_doms(
    session: AsyncSession,
    user_id: uuid.UUID,
    day: date,
    entries: dict[str, int],
) -> list[DailyMuscleDoms]:
    """Reemplaza el mapa de dolor del día por las entradas recibidas."""
    current = await get_doms(session, user_id, day)
    current_by_group = {row.muscle_group: row for row in current}
    saved: list[DailyMuscleDoms] = []
    for group, pain in entries.items():
        record = current_by_group.pop(group, None)
        if record is None:
            record = DailyMuscleDoms(
                user_id=user_id, date=day, muscle_group=group, pain=pain
            )
            session.add(record)
        else:
            record.pain = pain
        saved.append(record)
    for stale in current_by_group.values():
        await session.delete(stale)
    await session.commit()
    for record in saved:
        await session.refresh(record)
    return saved


async def get_calibration(
    session: AsyncSession, user_id: uuid.UUID
) -> dict[str, UserMuscleCalibration]:
    """Mapa muscle_group -> calibracion persistida del usuario."""
    result = await session.execute(
        select(UserMuscleCalibration).where(
            UserMuscleCalibration.user_id == user_id
        )
    )
    return {row.muscle_group: row for row in result.scalars().all()}


async def save_calibration(
    session: AsyncSession,
    user_id: uuid.UUID,
    params: dict[str, tuple[float, float, int, float | None]],
) -> None:
    """Persiste ng_delta, tau2_factor, sample_count y pearson_r por grupo."""
    current = await get_calibration(session, user_id)
    for group, (ng_delta, tau2_factor, samples, pearson_r) in params.items():
        record = current.get(group)
        if record is None:
            record = UserMuscleCalibration(
                user_id=user_id,
                muscle_group=group,
                ng_delta=ng_delta,
                tau2_factor=tau2_factor,
                sample_count=samples,
                pearson_r=pearson_r,
            )
            session.add(record)
        else:
            record.ng_delta = ng_delta
            record.tau2_factor = tau2_factor
            record.sample_count = samples
            record.pearson_r = pearson_r
    await session.commit()
