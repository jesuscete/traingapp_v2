"""Motor de fatiga: carga sesiones, readiness, DOMS y calibración, y simula.

Compartido por las estadísticas (/stats/fatigue*) y por el agente conversacional.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import calibration as calibration_analytics
from app.analytics import fatigue as fatigue_analytics
from app.crud import fatigue as fatigue_crud
from app.crud import stats as stats_crud
from app.services import fatigue_input


def _period_start(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


@dataclass(frozen=True)
class FatigueInputs:
    events: dict[date, list[fatigue_analytics.SessionData]]
    readiness: dict[date, fatigue_analytics.ReadinessData]
    doms: dict[date, dict[str, int]]
    weights: dict[str, dict[str, float]]
    tau2_factors: dict[str, float] | None
    today: date


async def fatigue_inputs(
    session: AsyncSession,
    user_id: uuid.UUID,
    days_back: int = 90,
    apply_calibration: bool = True,
) -> FatigueInputs:
    """Carga eventos, readiness, DOMS y pesos del periodo.

    Si `apply_calibration`, corrige `N_g` y `tau2` por grupo con la
    calibracion personal del usuario (ADR-015).
    """
    records = await stats_crud.sessions_in_range(
        session, user_id, _period_start(days_back)
    )
    readiness_rows = await fatigue_crud.readiness_since(
        session, user_id, (datetime.now(UTC) - timedelta(days=days_back)).date()
    )
    weights = await fatigue_crud.load_map(session)

    today = datetime.now(UTC).date()
    events: dict[date, list[fatigue_analytics.SessionData]] = defaultdict(list)
    for ts in records:
        events[ts.performed_at.date()].append(fatigue_input.session_data(ts))

    readiness_map = {
        row.date: fatigue_analytics.ReadinessData(
            sleep_hours=row.sleep_hours,
            doms=row.doms,
            rest_day=row.rest_day,
            hrv_score=row.hrv_score,
        )
        for row in readiness_rows
    }
    doms_map = await fatigue_crud.doms_map(
        session, user_id, (datetime.now(UTC) - timedelta(days=days_back)).date()
    )

    tau2_factors = None
    if apply_calibration:
        calibration_rows = await fatigue_crud.get_calibration(session, user_id)
        if calibration_rows:
            weights = {
                disc: {
                    group: round(
                        min(1.0, value * calibration_analytics.ng_factor(
                            calibration_rows[group].ng_delta
                        )),
                        3,
                    )
                    if group in calibration_rows
                    else value
                    for group, value in disc_weights.items()
                }
                for disc, disc_weights in weights.items()
            }
            tau2_factors = {
                group: row.tau2_factor
                for group, row in calibration_rows.items()
            }

    return FatigueInputs(events, readiness_map, doms_map, weights, tau2_factors, today)




async def simulate_fatigue(
    session: AsyncSession,
    user_id: uuid.UUID,
    days_back: int = 90,
    apply_calibration: bool = True,
) -> tuple[
    dict[date, dict[str, float]],
    dict[date, dict[str, float]],
    dict[date, dict[str, int]],
    dict[str, dict[str, float]],
    date,
]:
    """Simula la fatiga del periodo: (states, impulses, doms_by_group, weights, today)."""
    inp = await fatigue_inputs(session, user_id, days_back, apply_calibration)
    states, impulses = fatigue_analytics.simulate(
        inp.events,
        inp.readiness,
        inp.weights,
        inp.today,
        doms_by_group=inp.doms,
        tau2_factors=inp.tau2_factors,
    )
    return states, impulses, inp.doms, inp.weights, inp.today
