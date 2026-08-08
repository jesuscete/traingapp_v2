from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import computations, met
from app.analytics import fatigue as fatigue_analytics
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import fatigue as fatigue_crud
from app.crud import stats as stats_crud
from app.models import User
from app.schemas import stats as stats_schemas

router = APIRouter(prefix="/stats", tags=["stats"])


def _period_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@router.get("/energy", response_model=stats_schemas.EnergyOut)
async def stats_energy(
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.EnergyOut:
    """Necesidades calóricas estimadas (Mifflin-St Jeor × PAL)."""
    weight = current_user.weight_kg
    height = current_user.height_cm
    birth_year = current_user.birth_year
    sex = current_user.sex
    goal = current_user.goal

    age = None
    if birth_year is not None:
        age = datetime.now(UTC).year - birth_year

    bmr = None
    if weight and height and age and sex in ("male", "female"):
        bmr = met.bmr_mifflin(weight, height, age, is_male=(sex == "male"))

    tdee_value = None
    if bmr is not None:
        tdee_value = met.tdee(bmr, "moderate")

    return stats_schemas.EnergyOut(
        weight_kg=weight,
        height_cm=height,
        age=age,
        goal=goal,
        bmr_kcal=bmr,
        tdee_kcal=tdee_value,
        target_kcal=(
            met.target_kcal(tdee_value, goal) if tdee_value is not None else None
        ),
    )


@router.get("/fatigue", response_model=stats_schemas.FatigueOut)
async def stats_fatigue(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_days: Annotated[int, Query(alias="projectDays", ge=0, le=7)] = 0,
) -> stats_schemas.FatigueOut:
    """Fatiga muscular local (0-100 por grupo) + proyeccion residual."""
    days_back = 90
    records = await stats_crud.sessions_in_range(
        session, current_user.id, _period_start(days_back)
    )
    readiness_rows = await fatigue_crud.readiness_since(
        session, current_user.id, (datetime.now(UTC) - timedelta(days=days_back)).date()
    )
    weights = await fatigue_crud.load_map(session)

    today = datetime.now(UTC).date()
    events: dict[date, list[fatigue_analytics.SessionData]] = defaultdict(list)
    for ts in records:
        details = ts.details or {}
        rpe = details.get("rpe")
        strikes = details.get("strikes")
        events[ts.performed_at.date()].append(
            fatigue_analytics.SessionData(
                discipline=ts.discipline,
                duration_minutes=ts.duration_minutes,
                distance_meters=ts.distance_meters,
                volume_kg=ts.volume_kg,
                rpe=rpe if isinstance(rpe, int) else None,
                strikes=strikes if isinstance(strikes, int) else None,
                details=details,
            )
        )

    readiness_map = {
        row.date: fatigue_analytics.ReadinessData(
            sleep_hours=row.sleep_hours,
            doms=row.doms,
            rest_day=row.rest_day,
        )
        for row in readiness_rows
    }

    states, impulses = fatigue_analytics.simulate(
        events, readiness_map, weights, today
    )
    state_today = states.get(today, {g: 0.0 for g in fatigue_analytics.MUSCLE_GROUPS})
    state = fatigue_analytics.project(state_today, project_days)

    muscles: list[stats_schemas.FatigueMuscleOut] = []
    risks: list[stats_schemas.FatigueRiskOut] = []
    for group in fatigue_analytics.MUSCLE_GROUPS:
        value = round(state[group], 1)
        level = fatigue_analytics.fatigue_level(value)
        acwr = fatigue_analytics.acute_chronic_ratio(impulses, group, today)
        reasons: list[str] = []

        persisted = 0
        cursor = today
        while cursor in states and states[cursor][group] >= fatigue_analytics.WARN_LEVEL:
            persisted += 1
            cursor -= timedelta(days=1)
        if persisted >= 3:
            reasons.append(
                f"por encima del umbral {persisted:.0f} días consecutivos"
            )
        if acwr >= fatigue_analytics.ACWR_VERY_HIGH:
            reasons.append("carga semanal más del doble que la mensual")
        elif acwr >= fatigue_analytics.ACWR_HIGH:
            reasons.append("carga semanal muy superior a la mensual")

        muscles.append(
            stats_schemas.FatigueMuscleOut(
                muscle_group=group,
                fatigue=value,
                impulse_today=round(impulses.get(today, {}).get(group, 0.0), 1),
                level=level,
                acwr=acwr,
            )
        )
        if level != "ok" or reasons:
            risks.append(
                stats_schemas.FatigueRiskOut(
                    muscle_group=group,
                    level=level,
                    reasons=reasons,
                )
            )

    risks.sort(key=lambda item: item.level, reverse=True)
    fatigue_values = [item.fatigue for item in muscles]

    today_readiness = readiness_map.get(today)
    readiness_out = None
    if today_readiness is not None:
        readiness_out = stats_schemas.ReadinessOut(
            date=today,
            sleep_hours=today_readiness.sleep_hours,
            doms=today_readiness.doms,
            rest_day=today_readiness.rest_day,
        )

    return stats_schemas.FatigueOut(
        as_of=today,
        projected=today + timedelta(days=project_days),
        muscles=muscles,
        max_fatigue=round(max(fatigue_values, default=0.0), 1),
        avg_fatigue=round(
            sum(fatigue_values) / len(fatigue_values) if fatigue_values else 0.0, 1
        ),
        readiness=readiness_out,
        risks=risks,
    )


@router.get("/readiness", response_model=stats_schemas.ReadinessOut | None)
async def stats_readiness(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.ReadinessOut | None:
    """Readiness del dia de hoy del usuario."""
    row = await fatigue_crud.get_readiness(
        session, current_user.id, datetime.now(UTC).date()
    )
    if row is None:
        return None
    return stats_schemas.ReadinessOut(
        date=row.date,
        sleep_hours=row.sleep_hours,
        doms=row.doms,
        rest_day=row.rest_day,
        hrv_score=row.hrv_score,
        resting_hr=row.resting_hr,
    )


@router.post("/readiness", response_model=stats_schemas.ReadinessOut)
async def upsert_readiness(
    body: stats_schemas.ReadinessIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.ReadinessOut:
    """Registra sueno/DOMS/descanso/HRV del dia (afecta a la recuperacion)."""
    row = await fatigue_crud.upsert_readiness(
        session,
        current_user.id,
        body.date,
        sleep_hours=body.sleep_hours,
        doms=body.doms,
        rest_day=body.rest_day,
        hrv_score=body.hrv_score,
        resting_hr=body.resting_hr,
    )
    return stats_schemas.ReadinessOut(
        date=row.date,
        sleep_hours=row.sleep_hours,
        doms=row.doms,
        rest_day=row.rest_day,
        hrv_score=row.hrv_score,
        resting_hr=row.resting_hr,
    )


@router.get("/doms", response_model=stats_schemas.DomsOut | None)
async def stats_doms(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    day: date | None = None,
) -> stats_schemas.DomsOut | None:
    """DOMS localizado por grupo muscular del dia (mapa corporal)."""
    target = day or datetime.now(UTC).date()
    rows = await fatigue_crud.get_doms(session, current_user.id, target)
    return stats_schemas.DomsOut(
        date=target,
        entries=[
            stats_schemas.DomsEntryOut(muscle_group=row.muscle_group, pain=row.pain)
            for row in rows
        ],
    )


@router.post("/doms", response_model=stats_schemas.DomsOut)
async def upsert_doms(
    body: stats_schemas.DomsIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.DomsOut:
    """Registra el dolor muscular (0-10) por grupo para un dia (mapa corporal)."""
    entries = {entry.muscle_group: entry.pain for entry in body.entries}
    rows = await fatigue_crud.upsert_doms(session, current_user.id, body.date, entries)
    return stats_schemas.DomsOut(
        date=body.date,
        entries=[
            stats_schemas.DomsEntryOut(muscle_group=row.muscle_group, pain=row.pain)
            for row in rows
        ],
    )


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
