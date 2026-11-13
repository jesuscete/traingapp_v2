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

# Recuperación en dos compartimentos (M4.1):
# - agudo (neural/metabólico): se va en horas, igual en todos los grupos;
# - residual (daño muscular / DOMS): días, más lento en grupos grandes y excéntricos.
ACUTE_SHARE = 0.35
TAU_ACUTE = 0.5  # días (~12 h)
TAU_RESIDUAL: dict[str, float] = {
    "quadriceps": 3.0,
    "hamstrings": 3.0,
    "glutes": 2.6,
    "back": 2.6,
    "chest": 2.4,
    "shoulders": 2.2,
    "calves": 2.0,
    "biceps": 1.9,
    "triceps": 1.9,
    "neck": 1.8,
    "core": 1.7,
    "forearms": 1.6,
}
# Saturación: más volumen sigue sumando con rendimiento decreciente (sin tope duro).
SATURATION_K = 1.6  # volumen relativo 1.0 -> 80 % del impulso máximo
GYM_REF_SETS = 6.0  # series efectivas por grupo para 1-e^-1 (63 %); 10 series -> 81 %
TRIMP_REF = 100.0  # TRIMP de ~1 h a ritmo medio-alto = volumen relativo 1.0 (M6)
# WOD (CrossFit/HYROX): minutos de trabajo para volumen relativo 1.0 en el músculo principal
# de todos los movimientos (con SATURATION_K: 20 min -> ~66 %, una carrera HYROX -> ~95 %).
WOD_REF_MINUTES = 30.0

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
CYCLING_REF_KM = 40.0
SWIMMING_REF_KM = 2.5
COMBAT_DISCIPLINES = frozenset({"boxing", "martial_arts"})

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
    session_id: str | None = None
    label: str | None = None
    # Volumen relativo por grupo ya repartido por músculos (gym: series efectivas /
    # GYM_REF_SETS; combate: bloques con sus pesos). Si existe, manda sobre los pesos
    # de la disciplina. `load_includes_effort` = el esfuerzo (RPE) ya va dentro.
    group_load: dict[str, float] | None = None
    load_includes_effort: bool = False


@dataclass(frozen=True)
class ReadinessData:
    """Readiness diaria (entradas subjetivas + futuras de agentes externos).

    `doms_by_group` (opcional) es el mapa corporal ADR-011: penaliza la
    recuperacion del grupo con dolor reportado sin cambiar el resto.
    """

    sleep_hours: float | None = None
    doms: int | None = None
    rest_day: bool = False
    hrv_score: float | None = None
    nutrition_score: float | None = None
    doms_by_group: dict[str, int] | None = None


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
    "crossfit": {
        "quadriceps": 0.85, "shoulders": 0.80, "core": 0.80, "glutes": 0.75,
        "back": 0.75, "hamstrings": 0.65, "triceps": 0.60, "forearms": 0.60,
        "chest": 0.50, "biceps": 0.45, "calves": 0.45, "neck": 0.20,
    },
    "hyrox": {
        "quadriceps": 0.95, "glutes": 0.85, "calves": 0.80, "hamstrings": 0.75,
        "core": 0.70, "back": 0.65, "forearms": 0.65, "shoulders": 0.60,
        "biceps": 0.40, "triceps": 0.40, "chest": 0.35, "neck": 0.15,
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


def compartment_factors(mod: float, group: str, tau2_factor: float = 1.0) -> tuple[float, float]:
    """Factores de recuperación diarios (agudo, residual) con el modulador m."""
    tau_residual = max(0.1, TAU_RESIDUAL.get(group, 2.2) * tau2_factor)
    return math.exp(-mod / TAU_ACUTE), math.exp(-mod / tau_residual)


def saturate(relative: float) -> float:
    """0-1 con rendimiento decreciente: 1 - e^(-k·v)."""
    return 1.0 - math.exp(-SATURATION_K * max(0.0, relative))


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


def mod_for_group(
    readiness: ReadinessData | None, day_doms: dict[str, int] | None, group: str
) -> float:
    """Modulador por grupo: m global ajustado por el DOMS localizado del grupo.

    El dolor reportado en el mapa corporal (ADR-011) penaliza la recuperacion
    del grupo: si `day_doms` trae el grupo, se sustituye el DOMS global por el
    local; si no, se usa el global.
    """
    if day_doms is not None and group in day_doms:
        local = ReadinessData(
            sleep_hours=readiness.sleep_hours if readiness else None,
            doms=day_doms[group],
            rest_day=readiness.rest_day if readiness else False,
            hrv_score=readiness.hrv_score if readiness else None,
            nutrition_score=readiness.nutrition_score if readiness else None,
        )
        return mod_from_readiness(local)
    return mod_from_readiness(readiness)


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
    """Volumen relativo sin tope (1.0 = sesión de referencia); se satura en session_load."""
    disc = data.discipline
    if disc in COMBAT_DISCIPLINES:
        strikes = estimate_strikes(data)
        details = data.details or {}
        bag = _as_float(details.get("bag_minutes"))
        rope = _as_float(details.get("jump_rope_minutes"))
        footwork = _as_float(details.get("footwork_minutes"))
        sparring = 1.0 if details.get("sparring") else 0.0
        vol = strikes + 25 * bag + 15 * rope + 8 * footwork + 40 * sparring
        return (vol / BOXING_REF_STRIKES)
    if disc == "running":
        km = (data.distance_meters or 0.0) / 1000.0
        if km > 0:
            gradient = _as_float((data.details or {}).get("avg_gradient"))
            return (km * (1 + gradient / 100) / RUNNING_REF_KM)
        return ((data.duration_minutes or 0) / RUNNING_REF_MIN)
    if disc in ("cycling", "swimming"):
        km = (data.distance_meters or 0.0) / 1000.0
        if km > 0:
            reference = CYCLING_REF_KM if disc == "cycling" else SWIMMING_REF_KM
            gradient = _as_float((data.details or {}).get("avg_gradient"))
            return (km * (1 + gradient / 100) / reference)
        return ((data.duration_minutes or 0) / GENERIC_REF_MIN)
    if disc == "gym":
        if data.volume_kg > 0:
            return (data.volume_kg / GYM_REF_KG)
        return ((data.duration_minutes or 0) / GENERIC_REF_MIN)
    return ((data.duration_minutes or 0) / GENERIC_REF_MIN)


def session_load(
    data: SessionData, weights: dict[str, dict[str, float]]
) -> dict[str, float]:
    """Impulso I_g (0-100) de una sesión para cada grupo."""
    intensity = 1.0 if data.load_includes_effort else (data.rpe or 5) / 10.0
    if data.group_load is not None:
        return {
            g: round(100 * (1.0 - math.exp(-data.group_load.get(g, 0.0))) * intensity, 1)
            for g in MUSCLE_GROUPS
        }
    discipline_weights = (
        weights.get(data.discipline)
        or MUSCLE_LOAD_DEFAULT.get(data.discipline)
        or MUSCLE_LOAD_DEFAULT["other"]
    )
    volume = saturate(relative_volume(data))
    return {
        group: round(100 * discipline_weights.get(group, 0.4) * volume * intensity, 1)
        for group in MUSCLE_GROUPS
    }


Compartments = dict[str, tuple[float, float]]  # grupo -> (agudo, residual)


def _day_factors(
    previous_date: date | None,
    readiness: dict[date, ReadinessData],
    doms_by_group: dict[date, dict[str, int]] | None,
    tau2_factors: dict[str, float] | None,
) -> Compartments:
    """Factores (agudo, residual) de cada grupo al pasar del día anterior al actual."""
    if previous_date is None:
        return {g: (1.0, 1.0) for g in MUSCLE_GROUPS}
    prior = readiness.get(previous_date)
    day_doms = doms_by_group.get(previous_date) if doms_by_group is not None else None
    return {
        g: compartment_factors(
            mod_for_group(prior, day_doms, g), g, (tau2_factors or {}).get(g, 1.0)
        )
        for g in MUSCLE_GROUPS
    }


@dataclass(frozen=True)
class Contribution:
    """Lo que una sesión aporta hoy a la fatiga de un grupo."""

    performed_on: date
    session: SessionData
    impulse: float
    remaining: float


def contributions(
    events: dict[date, list[SessionData]],
    readiness: dict[date, ReadinessData],
    weights: dict[str, dict[str, float]],
    today: date,
    group: str,
    doms_by_group: dict[date, dict[str, int]] | None = None,
    tau2_factors: dict[str, float] | None = None,
) -> list[Contribution]:
    """Descompone la fatiga actual de `group` por sesión (misma dinámica que `simulate`)."""
    if not events:
        return []
    start = min(min(events), today)
    tracked: list[tuple[date, SessionData, float, float, float]] = []
    previous_date: date | None = None
    current = start
    while current <= today:
        fa, fr = _day_factors(previous_date, readiness, doms_by_group, tau2_factors)[group]
        tracked = [(d, s, imp, a * fa, r * fr) for d, s, imp, a, r in tracked]
        for data in events.get(current, []):
            impulse = session_load(data, weights)[group]
            if impulse > 0:
                acute = ACUTE_SHARE * impulse
                tracked.append((current, data, impulse, acute, impulse - acute))
        previous_date = current
        current += timedelta(days=1)
    parts = [
        Contribution(performed_on=d, session=s, impulse=round(imp, 1), remaining=round(a + r, 1))
        for d, s, imp, a, r in tracked
    ]
    return sorted(parts, key=lambda c: c.remaining, reverse=True)


def simulate_compartments(
    events: dict[date, list[SessionData]],
    readiness: dict[date, ReadinessData],
    weights: dict[str, dict[str, float]],
    today: date,
    doms_by_group: dict[date, dict[str, int]] | None = None,
    tau2_factors: dict[str, float] | None = None,
) -> tuple[dict[date, Compartments], dict[date, dict[str, float]]]:
    """Recorre los días: recuperación por compartimento + impulso del día."""
    start = min(min(events), today) if events else today
    states: dict[date, Compartments] = {}
    impulses: dict[date, dict[str, float]] = {}
    previous: Compartments = {g: (0.0, 0.0) for g in MUSCLE_GROUPS}
    previous_date: date | None = None
    current = start
    while current <= today:
        factors = _day_factors(previous_date, readiness, doms_by_group, tau2_factors)
        state = {
            g: (previous[g][0] * factors[g][0], previous[g][1] * factors[g][1])
            for g in MUSCLE_GROUPS
        }
        day_impulses = {g: 0.0 for g in MUSCLE_GROUPS}
        for data in events.get(current, []):
            loads = session_load(data, weights)
            for g in MUSCLE_GROUPS:
                acute, residual = state[g]
                added_acute = ACUTE_SHARE * loads[g]
                state[g] = (acute + added_acute, residual + loads[g] - added_acute)
                day_impulses[g] += loads[g]
        states[current] = state
        impulses[current] = day_impulses
        previous = state
        previous_date = current
        current += timedelta(days=1)
    return states, impulses


def totals(compartments: Compartments) -> dict[str, float]:
    return {g: a + r for g, (a, r) in compartments.items()}


def simulate(
    events: dict[date, list[SessionData]],
    readiness: dict[date, ReadinessData],
    weights: dict[str, dict[str, float]],
    today: date,
    doms_by_group: dict[date, dict[str, int]] | None = None,
    tau2_factors: dict[str, float] | None = None,
) -> tuple[dict[date, dict[str, float]], dict[date, dict[str, float]]]:
    """Fatiga total por día (agudo + residual) e impulsos."""
    compartments, impulses = simulate_compartments(
        events, readiness, weights, today, doms_by_group, tau2_factors
    )
    return {d: totals(c) for d, c in compartments.items()}, impulses


def project(
    state: Compartments,
    days: int,
    tau2_factors: dict[str, float] | None = None,
) -> Compartments:
    """Compartimentos proyectados `days` adelante sin nuevas cargas (modulador neutro)."""
    result = dict(state)
    for _ in range(days):
        stepped: Compartments = {}
        for g, (acute, residual) in result.items():
            fa, fr = compartment_factors(1.0, g, (tau2_factors or {}).get(g, 1.0))
            stepped[g] = (acute * fa, residual * fr)
        result = stepped
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
