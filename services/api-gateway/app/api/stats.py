from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import calibration as calibration_analytics
from app.analytics import computations, met
from app.analytics import fatigue as fatigue_analytics
from app.analytics import insights as insights_analytics
from app.analytics import load as load_analytics
from app.analytics.catalog_seed import zone_of
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import fatigue as fatigue_crud
from app.crud import stats as stats_crud
from app.crud.disciplines import load_catalog
from app.models import User
from app.schemas import stats as stats_schemas
from app.services import fatigue_engine
from app.services import nutrition as nutrition_service

router = APIRouter(prefix="/stats", tags=["stats"])


def _period_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@router.get("/fatigue/explain", response_model=stats_schemas.FatigueExplainOut)
async def stats_fatigue_explain(
    group: Annotated[str, Query(min_length=2, max_length=40)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=7, le=90)] = 28,
) -> stats_schemas.FatigueExplainOut:
    if group not in fatigue_analytics.MUSCLE_GROUPS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown muscle group"
        )
    inp = await fatigue_engine.fatigue_inputs(session, current_user.id, days)
    parts = fatigue_analytics.contributions(
        inp.events,
        inp.readiness,
        inp.weights,
        inp.today,
        group,
        doms_by_group=inp.doms,
        tau2_factors=inp.tau2_factors,
    )
    total = sum(p.remaining for p in parts)
    return stats_schemas.FatigueExplainOut(
        group=group,
        fatigue=round(total, 1),
        sessions=[
            stats_schemas.FatigueContributionOut(
                session_id=p.session.session_id,
                performed_on=p.performed_on,
                discipline=p.session.discipline,
                label=p.session.label,
                impulse=p.impulse,
                remaining=p.remaining,
                share=round(p.remaining / total, 3) if total > 0 else 0.0,
            )
            for p in parts
            if p.remaining >= 0.5
        ],
    )


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
    """Fatiga muscular local (0-100 por grupo) + proyeccion 24/48/72h."""
    fatigue = await fatigue_engine.simulate_fatigue(
        session, current_user.id
    )
    states, impulses, today = fatigue.states, fatigue.impulses, fatigue.today
    state = fatigue.projected(project_days)

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
                zone=zone_of(group),
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

    projection: list[stats_schemas.FatigueProjectionOut] = []
    for days_ahead in (1, 2, 3):
        values = list(fatigue.projected(days_ahead).values())
        projection.append(
            stats_schemas.FatigueProjectionOut(
                days_ahead=days_ahead,
                date=today + timedelta(days=days_ahead),
                max_fatigue=round(max(values, default=0.0), 1),
                avg_fatigue=round(sum(values) / len(values) if values else 0.0, 1),
            )
        )

    today_readiness = {
        row.date: row for row in await fatigue_crud.readiness_since(session, current_user.id, today)
    }.get(today)
    readiness_out = None
    if today_readiness is not None:
        readiness_out = stats_schemas.ReadinessOut(
            date=today,
            sleep_hours=today_readiness.sleep_hours,
            doms=today_readiness.doms,
            rest_day=today_readiness.rest_day,
            hrv_score=today_readiness.hrv_score,
            resting_hr=today_readiness.resting_hr,
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
        projection=projection,
    )


@router.get("/fatigue/series", response_model=stats_schemas.FatigueSeriesOut)
async def stats_fatigue_series(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> stats_schemas.FatigueSeriesOut:
    """Serie temporal de fatiga por grupo (graficos y comparativas hoy/ayer/7d)."""
    fatigue = await fatigue_engine.simulate_fatigue(
        session, current_user.id, days_back=max(days, 14)
    )
    states, today = fatigue.states, fatigue.today
    start = today - timedelta(days=days - 1)
    series: list[stats_schemas.FatigueSeriesDayOut] = []
    for day in sorted(states):
        if day < start or day > today:
            continue
        values = states[day]
        muscles = [
            stats_schemas.FatigueSeriesMuscleOut(
                muscle_group=group,
                fatigue=round(values.get(group, 0.0), 1),
                zone=zone_of(group),
            )
            for group in fatigue_analytics.MUSCLE_GROUPS
        ]
        raw = list(values.values())
        series.append(
            stats_schemas.FatigueSeriesDayOut(
                date=day,
                max_fatigue=round(max(raw, default=0.0), 1),
                avg_fatigue=round(sum(raw) / len(raw) if raw else 0.0, 1),
                muscles=muscles,
            )
        )
    return stats_schemas.FatigueSeriesOut(period_days=days, series=series)


@router.get("/load", response_model=stats_schemas.LoadOut)
async def stats_load(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> stats_schemas.LoadOut:
    """Analisis de carga del periodo: volumen, intensidad, carga, monotonia y strain."""
    fatigue = await fatigue_engine.simulate_fatigue(
        session, current_user.id, days_back=days
    )
    states, impulses, today = fatigue.states, fatigue.impulses, fatigue.today
    state_today = states.get(today, {g: 0.0 for g in fatigue_analytics.MUSCLE_GROUPS})
    analysis = load_analytics.analyse(impulses, state_today)
    by_muscle_group = cast(
        list[dict[str, object]], analysis["by_muscle_group"]
    )
    return stats_schemas.LoadOut(
        period_days=days,
        total_load=analysis["total_load"],
        monotony=analysis["monotony"],
        strain=analysis["strain"],
        by_muscle_group=[
            stats_schemas.LoadMuscleOut(
                **item,
                zone=zone_of(str(item["muscle_group"])),
            )
            for item in by_muscle_group
        ],
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


@dataclass
class _CalibrationState:
    ng_delta: float = 0.0
    tau2_factor: float = 1.0
    sample_count: int = 0
    pearson_r: float | None = None


def _calibration_latest_pair(
    states: dict[date, dict[str, float]],
    doms_map: dict[date, dict[str, int]],
    group: str,
) -> tuple[float, int]:
    """Ultimo (fatiga predicha dia anterior, DOMS reportado) para un grupo."""
    for day in sorted(doms_map, reverse=True):
        if group in doms_map[day]:
            prev = states.get(day - timedelta(days=1))
            predicted = prev.get(group, 0.0) if prev else 0.0
            return predicted, doms_map[day][group]
    return 0.0, 0


def _calibration_out(
    states: dict[date, dict[str, float]],
    doms_map: dict[date, dict[str, int]],
    params: dict[str, _CalibrationState],
    today: date,
) -> stats_schemas.CalibrationOut:
    groups: list[stats_schemas.CalibrationGroupOut] = []
    for group in fatigue_analytics.MUSCLE_GROUPS:
        predicted, pain = _calibration_latest_pair(states, doms_map, group)
        delta = round(
            calibration_analytics.clamp(
                (pain - predicted / 10.0) / 10.0, -0.15, 0.15
            ),
            4,
        )
        state = params.get(group)
        ng_delta = state.ng_delta if state else 0.0
        tau2_factor = state.tau2_factor if state else 1.0
        samples = state.sample_count if state else 0
        groups.append(
            stats_schemas.CalibrationGroupOut(
                muscle_group=group,
                predicted_fatigue=round(predicted, 1),
                reported_doms=pain,
                delta=delta,
                ng_delta=ng_delta,
                ng_factor=calibration_analytics.ng_factor(ng_delta),
                tau2_factor=tau2_factor,
                sample_count=samples,
                confidence_level=calibration_analytics.confidence_level(samples),
            )
        )
    total_samples = max((s.sample_count for s in params.values()), default=0)
    pearson_r = next((s.pearson_r for s in params.values() if s.pearson_r is not None), None)
    return stats_schemas.CalibrationOut(
        as_of=today,
        confidence_level=calibration_analytics.confidence_level(total_samples),
        pearson_r=pearson_r,
        groups=groups,
    )


@router.get("/calibration", response_model=stats_schemas.CalibrationOut)
async def stats_calibration(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.CalibrationOut:
    """Estado del calibrador DOMS vs fatiga (spec 7.3)."""
    fatigue = await fatigue_engine.simulate_fatigue(
        session, current_user.id, days_back=60, apply_calibration=False
    )
    states, doms_map, today = fatigue.states, fatigue.doms, fatigue.today
    rows = await fatigue_crud.get_calibration(session, current_user.id)
    params = {
        group: _CalibrationState(
            ng_delta=row.ng_delta,
            tau2_factor=row.tau2_factor,
            sample_count=row.sample_count,
            pearson_r=row.pearson_r,
        )
        for group, row in rows.items()
    }
    return _calibration_out(states, doms_map, params, today)


@router.post("/calibration", response_model=stats_schemas.CalibrationOut)
async def apply_calibration(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> stats_schemas.CalibrationOut:
    """Aplica un paso de gradiente con el DOMS reportado y persiste (spec 7.3)."""
    fatigue = await fatigue_engine.simulate_fatigue(
        session, current_user.id, days_back=60, apply_calibration=False
    )
    states, doms_map, today = fatigue.states, fatigue.doms, fatigue.today
    current = await fatigue_crud.get_calibration(session, current_user.id)

    window_start = today - timedelta(days=30)
    pairs_by_group: dict[str, list[tuple[float, float]]] = {
        g: [] for g in fatigue_analytics.MUSCLE_GROUPS
    }
    for day, day_doms in doms_map.items():
        if not (window_start <= day <= today):
            continue
        prev = states.get(day - timedelta(days=1))
        if prev is None:
            continue
        for group, pain in day_doms.items():
            if group in pairs_by_group:
                pairs_by_group[group].append((prev.get(group, 0.0) / 10.0, float(pain)))

    params: dict[str, _CalibrationState] = {}
    global_pairs: list[tuple[float, float]] = []
    for group in fatigue_analytics.MUSCLE_GROUPS:
        pairs = pairs_by_group[group]
        if not pairs:
            continue
        global_pairs.extend(pairs)
        predicted = sum(p[0] for p in pairs) / len(pairs)
        reported = sum(p[1] for p in pairs) / len(pairs)
        step = calibration_analytics.gradient_step(
            {group: predicted}, {group: reported}
        )
        ng_delta = calibration_analytics.apply_gradient(
            {group: current[group].ng_delta if group in current else 0.0}, step
        )[group]
        params[group] = _CalibrationState(
            ng_delta=ng_delta,
            tau2_factor=calibration_analytics.tau2_factor_from(
                {group: ng_delta}
            )[group],
            sample_count=len(pairs),
        )

    pearson_r = calibration_analytics.pearson(global_pairs)
    for state in params.values():
        state.pearson_r = pearson_r

    if params:
        await fatigue_crud.save_calibration(
            session,
            current_user.id,
            {
                group: (
                    state.ng_delta,
                    state.tau2_factor,
                    state.sample_count,
                    state.pearson_r,
                )
                for group, state in params.items()
            },
        )

    return _calibration_out(states, doms_map, params, today)


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
    catalog = await load_catalog(session)
    return stats_schemas.CardioOut(
        **asdict(computations.compute_cardio(records, catalog.cardio_codes)),
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


@router.get("/home", response_model=stats_schemas.HomeOut)
async def stats_home(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    hour: Annotated[int | None, Query(ge=0, le=23)] = None,
    today: date | None = None,
) -> stats_schemas.HomeOut:
    """Resumen de inicio: avisos deterministas y semana por deporte (minutos, no kg)."""
    day = today or datetime.now(UTC).date()
    records = await stats_crud.sessions_in_range(
        session, current_user.id, _period_start(30)
    )
    week_start = day - timedelta(days=6)
    prev_start = week_start - timedelta(days=7)
    by_sport: dict[str, stats_schemas.WeekSportOut] = {}
    week_minutes = prev_minutes = 0
    for record in records:
        performed = record.performed_at.date()
        minutes = record.duration_minutes or 0
        if week_start <= performed <= day:
            week_minutes += minutes
            item = by_sport.setdefault(
                record.discipline,
                stats_schemas.WeekSportOut(
                    discipline=record.discipline, sessions=0, minutes=0, distance_m=0
                ),
            )
            item.sessions += 1
            item.minutes += minutes
            item.distance_m += record.distance_meters or 0
        elif prev_start <= performed < week_start:
            prev_minutes += minutes

    fatigue = await fatigue_engine.simulate_fatigue(session, current_user.id)
    state = fatigue.projected(0)
    groups = fatigue_analytics.MUSCLE_GROUPS
    tired = sorted(
        (g for g in groups if state[g] >= fatigue_analytics.WARN_LEVEL),
        key=lambda g: -state[g],
    )
    overloaded = [
        g
        for g in groups
        if fatigue_analytics.acute_chronic_ratio(fatigue.impulses, g, fatigue.today)
        >= fatigue_analytics.ACWR_HIGH
    ]
    nutrition_day = await nutrition_service.day_summary(session, current_user, day)
    goal = await nutrition_service.get_goal(session, current_user.id)
    weight = await nutrition_service.weight_history(session, current_user.id, 14, day)

    facts = insights_analytics.InsightFacts(
        today=day,
        session_dates=[r.performed_at.date() for r in records],
        week_minutes=week_minutes,
        prev_week_minutes=prev_minutes,
        tired_groups=tired,
        overloaded_groups=overloaded,
        meals_today=sum(len(m) for m in nutrition_day.meals.values()),
        protein_g=nutrition_day.totals.protein_g,
        protein_target_g=nutrition_day.target.protein_g if nutrition_day.target else None,
        goal=goal.goal,
        weight_change_week_kg=weight.change_week_kg,
        hour=hour,
    )
    week_dates = facts.session_dates
    return stats_schemas.HomeOut(
        insights=[
            stats_schemas.HomeInsightOut(**asdict(i))
            for i in insights_analytics.build_insights(facts)
        ],
        days_since_last=insights_analytics.days_since_last(facts),
        week_sessions=insights_analytics.sessions_last_week(facts),
        week_minutes=week_minutes,
        prev_week_minutes=prev_minutes,
        week_by_sport=sorted(by_sport.values(), key=lambda s: -s.minutes),
        active_days=sorted({d for d in week_dates if week_start <= d <= day}),
    )
