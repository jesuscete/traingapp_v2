from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import computations
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import stats as stats_crud
from app.models import User
from app.schemas import stats as stats_schemas

router = APIRouter(prefix="/stats", tags=["stats"])


def _period_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@router.get("/overview", response_model=stats_schemas.OverviewOut)
async def stats_overview(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> stats_schemas.OverviewOut:
    records = await stats_crud.sessions_in_range(
        session, current_user.id, _period_start(days)
    )
    return stats_schemas.OverviewOut(
        **asdict(computations.compute_overview(records, days)),
        period_days=days,
    )


@router.get("/volume", response_model=stats_schemas.VolumeOut)
async def stats_volume(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 90,
) -> stats_schemas.VolumeOut:
    records = await stats_crud.sessions_in_range(
        session, current_user.id, _period_start(days)
    )
    return stats_schemas.VolumeOut(
        **asdict(computations.compute_volume(records)),
        period_days=days,
    )


@router.get("/cardio", response_model=stats_schemas.CardioOut)
async def stats_cardio(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> stats_schemas.CardioOut:
    records = await stats_crud.sessions_in_range(
        session, current_user.id, _period_start(days)
    )
    return stats_schemas.CardioOut(
        **asdict(computations.compute_cardio(records)),
        period_days=days,
    )


@router.get("/progress", response_model=stats_schemas.ProgressOut)
async def stats_progress(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=182)] = 30,
) -> stats_schemas.ProgressOut:
    now = datetime.now(UTC)
    current = await stats_crud.sessions_in_range(
        session, current_user.id, now - timedelta(days=days)
    )
    previous = await stats_crud.sessions_in_range(
        session, current_user.id, now - timedelta(days=2 * days), now - timedelta(days=days)
    )
    return stats_schemas.ProgressOut(
        **asdict(computations.compute_progress(current, previous)),
        period_days=days,
    )
