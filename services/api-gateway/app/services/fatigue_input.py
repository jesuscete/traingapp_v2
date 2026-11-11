"""Traduce sesiones de BD a la entrada pura del modelo de fatiga."""

from pydantic import ValidationError

from app.analytics.fatigue import SessionData
from app.models import TrainingSession
from app.schemas.metrics import CombatMetrics, EnduranceMetrics

# Golpes equivalentes por minuto según el tipo de bloque (carga relativa, no conteo real).
COMBAT_STRIKES_PER_MIN: dict[str, float] = {
    "saco": 100,
    "sparring": 120,
    "manoplas": 110,
    "sombra": 60,
    "tecnica": 50,
    "comba": 30,
    "fisico": 60,
}


def _valid_rpe(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    rounded = round(value)
    return rounded if 1 <= rounded <= 10 else None


def session_rpe(ts: TrainingSession) -> int | None:
    """RPE de la sesión: details.rpe -> intensity -> RPE medio de las series."""
    details = ts.details or {}
    for candidate in (details.get("rpe"), ts.intensity):
        rpe = _valid_rpe(candidate)
        if rpe is not None:
            return rpe
    summary = ts.__dict__.get("summary")  # solo si se cargó; evita lazy-load en async
    return _valid_rpe(summary.avg_rpe) if summary is not None else None


def _metrics(details: dict[str, object]) -> CombatMetrics | EnduranceMetrics | None:
    raw = details.get("metrics")
    if not isinstance(raw, dict):
        return None
    try:
        if raw.get("kind") == "combat":
            return CombatMetrics.model_validate(raw)
        if raw.get("kind") == "endurance":
            return EnduranceMetrics.model_validate(raw)
    except ValidationError:
        return None
    return None


def combat_strikes(metrics: CombatMetrics) -> int:
    total = 0.0
    for block in metrics.blocks:
        if block.strikes is not None:
            total += block.strikes
        else:
            total += block.total_minutes() * COMBAT_STRIKES_PER_MIN.get(block.type, 80)
    return round(total)


def session_data(ts: TrainingSession) -> SessionData:
    details = dict(ts.details or {})
    strikes = details.get("strikes")
    metrics = _metrics(details)
    if isinstance(metrics, CombatMetrics):
        strikes = combat_strikes(metrics)
    distance = ts.distance_meters
    if isinstance(metrics, EnduranceMetrics):
        distance = distance or metrics.distance_meters
        elevation = metrics.elevation_gain_m or ts.elevation_gain_m
        if elevation and distance:
            details.setdefault("avg_gradient", round(elevation / distance * 100, 2))
    return SessionData(
        discipline=ts.discipline,
        duration_minutes=ts.duration_minutes,
        distance_meters=distance,
        volume_kg=ts.volume_kg,
        rpe=session_rpe(ts),
        strikes=strikes if isinstance(strikes, int) else None,
        details=details,
        session_id=str(ts.id),
        label=ts.raw_text,
    )
