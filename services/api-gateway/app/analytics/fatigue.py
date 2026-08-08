"""Modelo de fatiga muscular local (0-100 por grupo).

Especificación completa en `docs/architecture/fatigue-spec.md` (ADR-009).

Modelo impulso-respuesta con doble exponencial (familia Banister/Fitz-Clarke):
  F_g(d) = A_g(d) * F_g(d-1) + I_g(d)
  A_g(d) = k1*exp(-m(d)/tau1) + k2*exp(-m(d)/tau2)

- I_g: impulso de carga del día para el grupo g (0-100), dependiente de la
  ponderacion del grupo en la disciplina y del volumen/intensidad relativos.
- m: modulador de recuperacion (sueno, DOMS, descanso; HRV/nutricion listos
  para agentes externos). m=1 neutro, m<1 acelera, m>1 frena la recuperacion.
- Los 12 grupos se numeran con claves internas en ingles (codigo/API) y se
  traducen en la UI. La tabla de ponderaciones vive en la BD
  (`discipline_muscle_load`); MUSCLE_LOAD_DEFAULT es la referencia semilla y
  el fallback para tests.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

MUSCLE_GROUPS = [
    "quadriceps",
    "hamstrings",
    "glutes",
    "calves",
    "core",
    "back",
    "chest",
    "shoulders",
    "biceps",
    "triceps",
    "forearms",
    "neck",
]

# Constantes de recuperacion (dias). k1+k2 = 1.
K1 = 0.30
K2 = 0.70
TAU1 = 0.5  # fatiga aguda/neural (~12 h)
TAU2 = 3.0  # fatiga periferica/daño (DOMS)

# Umbrales de riesgo local.
WARN_LEVEL = 70.0
DANGER_LEVEL = 85.0
ACWR_HIGH = 1.5
ACWR_VERY_HIGH = 2.0

# Referencias de volumen para normalizar V_rel (cap 1.0).
BOXING_REF_STRIKES = 2000.0
RUNNING_REF_KM = 10.0
RUNNING_REF_MIN = 60.0
GYM_REF_KG = 15000.0
GENERIC_REF_MIN = 90.0

# Estimacion de golpes por minuto segun el tipo de sesion (sin datos reales).
STRIKES_PER_MIN = {"sparring": 120, "technique": 80, "bag": 100}
DEFAULT_STRIKES_PER_MIN = 80


@dataclass(frozen=True)
class SessionData:
    """Datos de una sesion necesarios para el impulso de fatiga."""

    discipline: str
    duration_minutes: int | None = None
    distance_meters: float | None = None
    volume_kg: float = 0.0
    rpe: int | None = None
    strikes: int | None = None
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class ReadinessData:
    """Readiness diaria (entradas subjetivas + futuras de agentes externos)."""

    sleep_hours: float | None = None
    doms: int | None = None
    rest_day: bool = False
    hrv_score: float | None = None
    nutrition_score: float | None = None


# Tabla de ponderaciones por disciplina (N_g en [0, 1]). Referencia semilla de
# `discipline_muscle_load`. Documentada en `docs/architecture/fatigue-spec.md`.
MUSCLE_LOAD_DEFAULT: dict[str, dict[str, float]] = {
    "boxing": {
        "shoulders": 0.95, "triceps": 0.85, "forearms": 0.80, "core": 0.90,
        "neck": 0.70, "biceps": 0.55, "quadriceps": 0.55, "back": 0.50,
        "glutes": 0.45, "hamstrings": 0.45, "calves": 0.45, "chest": 0.40,
    },
    "running": {
        "calves": 0.95, "quadriceps": 0.85, "hamstrings": 0.85, "glutes": 0.70,
        "core": 0.45, "back": 0.30, "neck": 0.20, "shoulders": 0.20,
        "chest": 0.10, "biceps": 0.10, "triceps": 0.10, "forearms": 0.10,
    },
    "gym": {
        "chest": 0.80, "back": 0.75, "shoulders": 0.70, "biceps": 0.65,
        "triceps": 0.65, "quadriceps": 0.65, "core": 0.55, "glutes": 0.50,
        "forearms": 0.45, "hamstrings": 0.45, "calves": 0.35, "neck": 0.30,
    },
    "calisthenics": {
        "core": 0.90, "back": 0.85, "shoulders": 0.85, "biceps": 0.85,
        "triceps": 0.85, "chest": 0.80, "forearms": 0.75, "quadriceps": 0.55,
        "calves": 0.45, "glutes": 0.40, "neck": 0.30, "hamstrings": 0.30,
    },
    "football": {
        "quadriceps": 0.90, "hamstrings": 0.90, "glutes": 0.80, "calves": 0.90,
        "core": 0.50, "back": 0.30, "chest": 0.20, "shoulders": 0.30,
        "biceps": 0.20, "triceps": 0.20, "forearms": 0.10, "neck": 0.20,
    },
    "badminton": {
        "calves": 0.90, "shoulders": 0.85, "quadriceps": 0.80, "triceps": 0.75,
        "hamstrings": 0.70, "forearms": 0.70, "glutes": 0.60, "core": 0.60,
        "biceps": 0.40, "back": 0.40, "chest": 0.30, "neck": 0.20,
    },
    "basketball": {
        "calves": 0.95, "quadriceps": 0.90, "glutes": 0.85, "hamstrings": 0.70,
        "core": 0.55, "shoulders": 0.55, "back": 0.40, "triceps": 0.40,
        "biceps": 0.35, "forearms": 0.35, "chest": 0.30, "neck": 0.15,
    },
    "table_tennis": {
        "forearms": 0.85, "shoulders": 0.85, "triceps": 0.75, "core": 0.60,
        "back": 0.50, "calves": 0.50, "biceps": 0.45, "quadriceps": 0.45,
        "chest": 0.35, "hamstrings": 0.35, "glutes": 0.30, "neck": 0.20,
    },
    "volleyball": {
        "calves": 0.95, "quadriceps": 0.90, "shoulders": 0.85, "glutes": 0.85,
        "triceps": 0.80, "hamstrings": 0.75, "core": 0.60, "forearms": 0.55,
        "back": 0.45, "biceps": 0.40, "chest": 0.35, "neck": 0.20,
    },
    "tennis": {
        "shoulders": 0.90, "calves": 0.85, "triceps": 0.80, "forearms": 0.80,
        "quadriceps": 0.75, "hamstrings": 0.70, "glutes": 0.70, "core": 0.70,
        "biceps": 0.50, "back": 0.50, "chest": 0.40, "neck": 0.25,
    },
    "swimming": {
        "shoulders": 0.90, "chest": 0.85, "triceps": 0.85, "core": 0.80,
        "back": 0.80, "biceps": 0.70, "calves": 0.60, "forearms": 0.60,
        "quadriceps": 0.55, "glutes": 0.45, "neck": 0.40, "hamstrings": 0.40,
    },
    "cricket": {
        "shoulders": 0.75, "core": 0.70, "calves": 0.70, "hamstrings": 0.60,
        "triceps": 0.60, "forearms": 0.60, "quadriceps": 0.55, "glutes": 0.55,
        "back": 0.45, "biceps": 0.40, "chest": 0.35, "neck": 0.35,
    },
    "golf": {
        "core": 0.75, "forearms": 0.70, "back": 0.65, "shoulders": 0.65,
        "triceps": 0.55, "biceps": 0.50, "chest": 0.45, "quadriceps": 0.45,
        "glutes": 0.40, "calves": 0.35, "hamstrings": 0.35, "neck": 0.25,
    },
    "baseball": {
        "shoulders": 0.85, "triceps": 0.80, "calves": 0.80, "forearms": 0.80,
        "hamstrings": 0.70, "core": 0.70, "quadriceps": 0.65, "glutes": 0.60,
        "back": 0.50, "biceps": 0.45, "chest": 0.40, "neck": 0.30,
    },
    "martial_arts": {
        "shoulders": 0.90, "core": 0.85, "triceps": 0.85, "calves": 0.85,
        "quadriceps": 0.80, "hamstrings": 0.75, "forearms": 0.75, "glutes": 0.70,
        "biceps": 0.70, "neck": 0.60, "back": 0.60, "chest": 0.50,
    },
    "hockey": {
        "quadriceps": 0.90, "calves": 0.90, "hamstrings": 0.85, "glutes": 0.80,
        "forearms": 0.65, "core": 0.60, "shoulders": 0.55, "back": 0.50,
        "triceps": 0.50, "biceps": 0.45, "chest": 0.30, "neck": 0.25,
    },
    "rugby": {
        "quadriceps": 0.90, "hamstrings": 0.85, "glutes": 0.85, "core": 0.85,
        "shoulders": 0.80, "calves": 0.75, "back": 0.70, "neck": 0.70,
        "chest": 0.60, "triceps": 0.60, "biceps": 0.55, "forearms": 0.55,
    },
    "handball": {
        "shoulders": 0.90, "calves": 0.90, "triceps": 0.85, "quadriceps": 0.85,
        "hamstrings": 0.75, "glutes": 0.75, "core": 0.70, "forearms": 0.70,
        "back": 0.50, "biceps": 0.50, "chest": 0.45, "neck": 0.25,
    },
    "climbing": {
        "forearms": 0.95, "back": 0.90, "shoulders": 0.90, "biceps": 0.90,
        "core": 0.85, "triceps": 0.80, "chest": 0.60, "calves": 0.65,
        "quadriceps": 0.55, "glutes": 0.40, "neck": 0.30, "hamstrings": 0.40,
    },
    "ski_snowboard": {
        "quadriceps": 0.95, "glutes": 0.80, "core": 0.75, "calves": 0.70,
        "hamstrings": 0.70, "forearms": 0.55, "back": 0.45, "shoulders": 0.45,
        "triceps": 0.40, "biceps": 0.35, "chest": 0.35, "neck": 0.30,
    },
    "cycling": {
        "quadriceps": 0.95, "glutes": 0.85, "calves": 0.70, "hamstrings": 0.60,
        "core": 0.50, "back": 0.45, "forearms": 0.45, "triceps": 0.35,
        "biceps": 0.30, "shoulders": 0.30, "neck": 0.30, "chest": 0.20,
    },
    "other": {group: 0.40 for group in MUSCLE_GROUPS},
}


def _as_float(value: object | None, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def decay(mod: float) -> float:
    """Factor de decaimiento diario para el modulador de recuperacion m."""
    return K1 * math.exp(-mod / TAU1) + K2 * math.exp(-mod / TAU2)


def mod_from_readiness(readiness: ReadinessData | None) -> float:
    """Dias efectivos de recuperacion m: >1 acelera, <1 frena.

    Entra en e^(-m/tau): un m mayor deja menos fatiga residual al dia siguiente.
    Los valores ausentes son neutros; solo se aplica cuando hay registro del dia.
    """
    if readiness is None:
        return 1.0
    sleep_score = (
        min(1.0, readiness.sleep_hours / 8.0)
        if readiness.sleep_hours is not None
        else 0.5
    )
    hrv_score = readiness.hrv_score if readiness.hrv_score is not None else 0.5
    nutrition = (
        readiness.nutrition_score if readiness.nutrition_score is not None else 0.5
    )
    doms_base = (readiness.doms or 0) / 10.0
    rest = 1.0 if readiness.rest_day else 0.0
    return (
        1.0
        + 0.25 * (sleep_score - 0.5)
        + 0.15 * (hrv_score - 0.5)
        - 0.10 * doms_base
        + 0.15 * rest
        + 0.05 * (nutrition - 0.5)
    )


def estimate_strikes(data: SessionData) -> int:
    """Golpes estimados a partir de rounds/tipo o detalles, si no hay cuenta real."""
    if data.strikes is not None:
        return data.strikes
    details = data.details or {}
    rounds = details.get("rounds")
    if isinstance(rounds, (int, float)) and rounds > 0:
        return int(rounds * DEFAULT_STRIKES_PER_MIN)
    minutes = data.duration_minutes or 0
    kind = details.get("kind")
    if isinstance(kind, str):
        rate = STRIKES_PER_MIN.get(kind, DEFAULT_STRIKES_PER_MIN)
        return int(minutes * rate)
    return int(minutes * DEFAULT_STRIKES_PER_MIN)


def relative_volume(data: SessionData) -> float:
    """Volumen relativo V_rel (cap 1.0) para normalizar el impulso."""
    disc = data.discipline
    if disc == "boxing":
        strikes = estimate_strikes(data)
        details = data.details or {}
        bag = _as_float(details.get("bag_minutes"))
        rope = _as_float(details.get("jump_rope_minutes"))
        footwork = _as_float(details.get("footwork_minutes"))
        sparring = 1.0 if details.get("sparring") else 0.0
        vol = strikes + 25 * bag + 15 * rope + 8 * footwork + 40 * sparring
        return min(1.0, vol / BOXING_REF_STRIKES)
    if disc == "running":
        km = (data.distance_meters or 0.0) / 1000.0
        if km > 0:
            gradient = _as_float((data.details or {}).get("avg_gradient"))
            return min(1.0, km * (1 + gradient / 100) / RUNNING_REF_KM)
        return min(1.0, (data.duration_minutes or 0) / RUNNING_REF_MIN)
    if disc == "gym":
        if data.volume_kg > 0:
            return min(1.0, data.volume_kg / GYM_REF_KG)
        return min(1.0, (data.duration_minutes or 0) / GENERIC_REF_MIN)
    return min(1.0, (data.duration_minutes or 0) / GENERIC_REF_MIN)


def session_load(
    data: SessionData, weights: dict[str, dict[str, float]]
) -> dict[str, float]:
    """Impulso I_g (0-100) de una sesion para cada grupo."""
    discipline_weights = (
        weights.get(data.discipline)
        or MUSCLE_LOAD_DEFAULT.get(data.discipline)
        or MUSCLE_LOAD_DEFAULT["other"]
    )
    v_rel = relative_volume(data)
    intensity = (data.rpe or 5) / 10.0
    return {
        group: round(100 * discipline_weights.get(group, 0.4) * v_rel * intensity, 1)
        for group in MUSCLE_GROUPS
    }


def simulate(
    events: dict[date, list[SessionData]],
    readiness: dict[date, ReadinessData],
    weights: dict[str, dict[str, float]],
    today: date,
) -> tuple[dict[date, dict[str, float]], dict[date, dict[str, float]]]:
    """Recorre dias aplicando decay + impulso; devuelve (estado, impulsos) por dia."""
    if events:
        start = min(events)
        if start > today:
            start = today
    else:
        start = today

    states: dict[date, dict[str, float]] = {}
    impulses: dict[date, dict[str, float]] = {}
    previous: dict[str, float] = {g: 0.0 for g in MUSCLE_GROUPS}
    previous_date: date | None = None
    current = start
    while current <= today:
        mod = (
            mod_from_readiness(readiness.get(previous_date))
            if previous_date is not None
            else 1.0
        )
        factor = decay(mod)
        state = {g: factor * previous[g] for g in MUSCLE_GROUPS}
        day_impulses: dict[str, float] = {g: 0.0 for g in MUSCLE_GROUPS}
        for data in events.get(current, []):
            loads = session_load(data, weights)
            for group in MUSCLE_GROUPS:
                state[group] += loads[group]
                day_impulses[group] += loads[group]
        states[current] = state
        impulses[current] = day_impulses
        previous = state
        previous_date = current
        current += timedelta(days=1)
    return states, impulses


def project(
    state: dict[str, float],
    days: int,
    mods: list[float] | None = None,
) -> dict[str, float]:
    """Fatiga residual proyectada `days` adelante sin nuevas cargas."""
    result = dict(state)
    for mod in mods or ([1.0] * days):
        factor = decay(mod)
        result = {g: factor * result[g] for g in MUSCLE_GROUPS}
    return result


def fatigue_level(fatigue: float) -> str:
    """Nivel de riesgo por grupo: ok | warning | danger."""
    if fatigue >= DANGER_LEVEL:
        return "danger"
    if fatigue >= WARN_LEVEL:
        return "warning"
    return "ok"


def acute_chronic_ratio(
    impulses: dict[date, dict[str, float]],
    group: str,
    today: date,
) -> float:
    """ACWR local: impulso de la ultima semana / promedio del ultimo mes."""
    short_window = sum(
        impulses.get(today - timedelta(days=offset), {}).get(group, 0.0)
        for offset in range(7)
    )
    long_window = sum(
        impulses.get(today - timedelta(days=offset), {}).get(group, 0.0)
        for offset in range(28)
    )
    if long_window <= 0:
        return 0.0
    return round(short_window / (long_window * (7 / 28)), 2)
