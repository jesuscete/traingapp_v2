import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import fatigue as fatigue_analytics
from app.models.fatigue import DailyReadiness, DisciplineMuscleLoad


async def load_map(
    session: AsyncSession,
) -> dict[str, dict[str, float]]:
    """Ponderaciones por disciplina desde el catalogo (fallback: defaults)."""
    result = await session.execute(select(DisciplineMuscleLoad))
    rows = list(result.scalars().all())
    if not rows:
        return dict(fatigue_analytics.MUSCLE_LOAD_DEFAULT)
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        grouped.setdefault(row.discipline, {})[row.muscle_group] = row.load
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
) -> DailyReadiness:
    record = await get_readiness(session, user_id, day)
    if record is None:
        record = DailyReadiness(
            user_id=user_id,
            date=day,
            sleep_hours=sleep_hours,
            doms=doms,
            rest_day=rest_day,
        )
        session.add(record)
    else:
        if sleep_hours is not None:
            record.sleep_hours = sleep_hours
        if doms is not None:
            record.doms = doms
        record.rest_day = rest_day
    await session.commit()
    await session.refresh(record)
    return record
