"""Traduce sesiones de BD a la entrada pura del modelo de fatiga (M3/M4.1).

- Gym: la carga de cada grupo sale de las SERIES REALES: por cada serie de trabajo,
  esfuerzo (RPE) x implicación del músculo en ese ejercicio (catálogo, principal = 1).
- Combate con bloques: golpes equivalentes por bloque repartidos con los pesos musculares
  de ese tipo de bloque (registro de deporte).
- Resto: pesos de la disciplina x volumen relativo (analytics.fatigue.relative_volume).
"""

import uuid
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from app.analytics import fatigue as fatigue_analytics
from app.analytics.catalog import muscle_group_of, normalize_exercise_name
from app.analytics.fatigue import SessionData
from app.models import TrainingSession, WorkoutExercise
from app.schemas.metrics import CombatMetrics, EnduranceMetrics
from app.services import sport_registry

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
DEFAULT_SET_RPE = 8.0
MIN_EFFORT = 0.5


@dataclass(frozen=True)
class MuscleMaps:
    """Implicación muscular del catálogo, por id de ejercicio y por nombre normalizado."""

    by_id: Mapping[uuid.UUID, Mapping[str, float]]
    by_name: Mapping[str, Mapping[str, float]]


def involvement(muscle_map: Mapping[str, float]) -> dict[str, float]:
    """Proporciones del catálogo -> implicación con el músculo principal a 1.0.

    Dominadas {back: 0.75, biceps: 0.25} -> {back: 1.0, biceps: 0.33}.
    """
    top = max(muscle_map.values(), default=0.0)
    if top <= 0:
        return {}
    return {g: round(v / top, 3) for g, v in muscle_map.items() if v > 0}


def set_effort(rpe: float | None) -> float:
    """Esfuerzo de una serie (0.5-1.0) según su RPE: RPE 10 = 1.0, RPE 8 = 0.88."""
    value = DEFAULT_SET_RPE if rpe is None else rpe
    return min(1.0, max(MIN_EFFORT, 0.4 + 0.06 * value))


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


def _exercise_involvement(we: WorkoutExercise, maps: MuscleMaps) -> dict[str, float]:
    muscle_map = (maps.by_id.get(we.exercise_id) if we.exercise_id else None) or maps.by_name.get(
        normalize_exercise_name(we.name)
    )
    if muscle_map:
        return involvement(muscle_map)
    group = muscle_group_of(we.name)  # ejercicio desconocido: heurística por nombre
    return {group: 1.0} if group in fatigue_analytics.MUSCLE_GROUPS else {}


def gym_group_load(ts: TrainingSession, maps: MuscleMaps) -> dict[str, float]:
    """Series efectivas por grupo / GYM_REF_SETS (volumen relativo por músculo)."""
    fallback_rpe = session_rpe(ts)
    effective: dict[str, float] = defaultdict(float)
    for we in ts.workout_exercises:
        weights = _exercise_involvement(we, maps)
        for ws in we.sets:
            if ws.is_warmup:
                continue
            rpes = [e.rpe for e in ws.entries if e.rpe is not None]
            effort = set_effort(max(rpes) if rpes else fallback_rpe)
            for group, weight in weights.items():
                effective[group] += effort * weight
    return {g: round(v / fatigue_analytics.GYM_REF_SETS, 4) for g, v in effective.items()}


def _metrics(details: Mapping[str, object]) -> CombatMetrics | EnduranceMetrics | None:
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


def block_strikes(block_type: str, minutes: float, strikes: int | None) -> float:
    if strikes is not None:
        return float(strikes)
    return minutes * COMBAT_STRIKES_PER_MIN.get(block_type, 80)


def combat_strikes(metrics: CombatMetrics) -> int:
    return round(sum(block_strikes(b.type, b.total_minutes(), b.strikes) for b in metrics.blocks))


def combat_group_load(discipline: str, metrics: CombatMetrics) -> dict[str, float]:
    """Volumen relativo por grupo: cada bloque carga sus músculos (comba -> gemelos...)."""
    default = fatigue_analytics.MUSCLE_LOAD_DEFAULT.get(discipline, {})
    load: dict[str, float] = defaultdict(float)
    for block in metrics.blocks:
        weights = sport_registry.block_weights(discipline, block.type) or default
        strikes = block_strikes(block.type, block.total_minutes(), block.strikes)
        for group, weight in weights.items():
            load[group] += strikes * weight
    scale = fatigue_analytics.SATURATION_K / fatigue_analytics.BOXING_REF_STRIKES
    return {g: round(v * scale, 4) for g, v in load.items()}


def trimp_of(details: Mapping[str, object]) -> float | None:
    value = details.get("trimp")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return float(value)


def trimp_group_load(discipline: str, trimp: float) -> dict[str, float]:
    """Actividad con pulsómetro: la carga sale del TRIMP (ya incluye la intensidad)."""
    weights = fatigue_analytics.MUSCLE_LOAD_DEFAULT.get(
        discipline, fatigue_analytics.MUSCLE_LOAD_DEFAULT["other"]
    )
    scale = fatigue_analytics.SATURATION_K * trimp / fatigue_analytics.TRIMP_REF
    return {g: round(w * scale, 4) for g, w in weights.items()}


def session_data(ts: TrainingSession, maps: MuscleMaps | None = None) -> SessionData:
    details = dict(ts.details or {})
    strikes = details.get("strikes")
    metrics = _metrics(details)
    group_load: dict[str, float] | None = None
    includes_effort = False
    if ts.workout_exercises and maps is not None:
        group_load, includes_effort = gym_group_load(ts, maps), True
    elif isinstance(metrics, CombatMetrics):
        strikes = combat_strikes(metrics)
        group_load = combat_group_load(ts.discipline, metrics)
    elif (trimp := trimp_of(details)) is not None:
        group_load, includes_effort = trimp_group_load(ts.discipline, trimp), True
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
        group_load=group_load,
        load_includes_effort=includes_effort,
    )
