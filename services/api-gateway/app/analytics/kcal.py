"""Estimacion hibrida de calorias (ADR-010).

Nucleo determinista y reproducible (ADR-006); la IA solo interpreta el texto
libre y sugiere RPE, nunca produce la cifra.

- Deportes (boxing, running, cycling, swimming, other): MET base del catalogo
  ajustado por RPE, frecuencia cardiaca media y tipo de sesion.
- Gym: trabajo mecanico (peso x reps x desplazamiento) + coste metabolico por
  minuto + EPOC, modulado por descansos entre series.

Devuelve siempre kcal + nivel de confianza + factores explicativos.
Todas las cifras son ESTIMACIONES (+-15%).
"""

from dataclasses import dataclass

from app.analytics import met

# Constantes del modelo gym.
REP_LIFT_TIME_S = 2.5  # tiempo bajo tension por repeticion (conc + exc)
LIFT_DISTANCE_M = 0.5  # desplazamiento neto medio del peso por repeticion
METABOLIC_EFFICIENCY = 0.22  # fraccion de energia quimica -> trabajo mecanico
GRAVITY = 9.81
KJ_TO_KCAL = 1 / 4.184

CARDIO_DISCIPLINES = frozenset({"boxing", "running", "cycling", "swimming", "other"})

# Factor por tipo de sesion (cardio): sin dato -> neutro 1.0.
WORKOUT_TYPE_FACTOR: dict[str, float] = {
    "interval": 1.20,
    "tempo": 1.10,
    "fartlek": 1.10,
    "long": 0.90,
    "easy": 0.80,
    "recovery": 0.70,
}


@dataclass(frozen=True)
class ExerciseInput:
    name: str
    weight_kg: float | None = None
    sets: int | None = None
    reps: int | None = None
    per_set_reps: list[int] | None = None
    rest_seconds: int | None = None


@dataclass(frozen=True)
class SessionKcalInput:
    discipline: str
    weight_kg: float | None
    duration_minutes: int | None
    rpe: int | None = None
    avg_heart_rate: float | None = None
    workout_type: str | None = None
    distance_meters: float | None = None
    exercises: tuple[ExerciseInput, ...] = ()
    kind: str | None = None
    met_value: float | None = None


@dataclass(frozen=True)
class KcalEstimate:
    kcal: float | None
    confidence: float  # 0-1
    confidence_level: str  # alta | media | baja
    factors: list[str]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _rpe_factor(rpe: int | None) -> float:
    if rpe is None:
        return 1.0
    return _clamp(0.5 + 0.1 * rpe, 0.6, 1.6)


def _is_cardio(input: SessionKcalInput) -> bool:
    """El catalogo (`kind`) manda; si no, cae al set historico."""
    if input.kind is not None:
        return input.kind == "cardio"
    return input.discipline in CARDIO_DISCIPLINES


def _hr_factor(avg_hr: float | None) -> float:
    """Razon de la FC media frente a ~70% HRmax (133 ppm de referencia)."""
    if avg_hr is None or avg_hr <= 0:
        return 1.0
    return _clamp(avg_hr / 133.0, 0.7, 1.5)


def _effective_reps(exercise: ExerciseInput) -> int:
    if exercise.per_set_reps:
        return sum(exercise.per_set_reps)
    if exercise.sets and exercise.reps:
        return exercise.sets * exercise.reps
    return 0


def _gym_mechanical_kcal(exercises: tuple[ExerciseInput, ...]) -> float:
    """Trabajo mecanico neto del levantamiento (kJ) convertido a kcal metabolicas."""
    total = 0.0
    for ex in exercises:
        reps = _effective_reps(ex)
        if ex.weight_kg and reps > 0:
            work_joules = ex.weight_kg * GRAVITY * LIFT_DISTANCE_M * reps
            work_kcal = work_joules * KJ_TO_KCAL / 1000 / METABOLIC_EFFICIENCY
            total += work_kcal
    return total


def _rest_factor(exercises: tuple[ExerciseInput, ...]) -> float:
    rests = [
        ex.rest_seconds
        for ex in exercises
        if ex.rest_seconds is not None and ex.rest_seconds > 0
    ]
    if not rests:
        return 1.0
    avg_rest = sum(rests) / len(rests)
    # Descansos cortos (<60s) elevan la intensidad; largos (>180s) la bajan.
    return _clamp(1 + 0.12 * (60 - avg_rest) / 120, 0.92, 1.12)


def _confidence(input: SessionKcalInput) -> float:
    score = 0.20
    if input.weight_kg is not None:
        score += 0.20
    if input.rpe is not None:
        score += 0.15
    if input.duration_minutes:
        score += 0.15
    if _is_cardio(input):
        if input.avg_heart_rate:
            score += 0.15
        if input.distance_meters:
            score += 0.15
    else:
        complete = [
            ex
            for ex in input.exercises
            if ex.weight_kg and _effective_reps(ex) > 0
        ]
        if complete:
            score += 0.15
        if any(ex.per_set_reps for ex in input.exercises):
            score += 0.05
        if any(ex.rest_seconds for ex in input.exercises):
            score += 0.05
    return round(_clamp(score, 0.0, 1.0), 2)


def _confidence_level(confidence: float) -> str:
    if confidence >= 0.70:
        return "alta"
    if confidence >= 0.45:
        return "media"
    return "baja"


def _factors(input: SessionKcalInput) -> list[str]:
    factors: list[str] = []
    if input.duration_minutes:
        factors.append(f"entrenamiento de {input.duration_minutes} minutos")
    if input.weight_kg is not None:
        factors.append(f"peso corporal de {input.weight_kg:g} kg")
    else:
        factors.append("sin peso corporal registrado (estimación menos precisa)")
    if input.rpe is not None:
        intensity = (
            "alta"
            if input.rpe >= 8
            else "media"
            if input.rpe >= 5
            else "baja"
        )
        factors.append(f"intensidad {intensity} (RPE {input.rpe})")
    if input.avg_heart_rate:
        factors.append(f"frecuencia cardíaca media de {input.avg_heart_rate:g} ppm")
    if input.distance_meters:
        factors.append(
            f"{input.distance_meters / 1000:.1f} km recorridos"
        )
    if not _is_cardio(input):
        volume = sum(
            ex.weight_kg * _effective_reps(ex)
            for ex in input.exercises
            if ex.weight_kg is not None
        )
        if volume >= 15000:
            factors.append("volumen elevado (tonelaje alto)")
        short_rests = [
            ex.rest_seconds
            for ex in input.exercises
            if ex.rest_seconds and ex.rest_seconds < 60
        ]
        if short_rests:
            factors.append("descansos cortos entre series")
    if _is_cardio(input) and input.workout_type:
        factors.append(f"tipo de sesión {input.workout_type}")
    return factors


def estimate(input: SessionKcalInput) -> KcalEstimate:
    minutes = float(input.duration_minutes or 0)
    if minutes <= 0 and not input.exercises:
        return KcalEstimate(
            kcal=None,
            confidence=_confidence(input),
            confidence_level=_confidence_level(_confidence(input)),
            factors=["sin duración ni ejercicios registrados"],
        )

    rpe_factor = _rpe_factor(input.rpe)
    if _is_cardio(input):
        if minutes <= 0 or input.weight_kg is None:
            return KcalEstimate(
                kcal=None,
                confidence=_confidence(input),
                confidence_level=_confidence_level(_confidence(input)),
                factors=["sin duración o peso corporal registrados (cardio)"],
            )
        met_base = (
            input.met_value
            if input.met_value is not None
            else met.met_for_discipline(input.discipline)
        )
        type_factor = WORKOUT_TYPE_FACTOR.get(input.workout_type or "", 1.0)
        effective_met = (
            met_base
            * rpe_factor
            * _hr_factor(input.avg_heart_rate)
            * type_factor
        )
        kcal = met.kcal_burned(effective_met, input.weight_kg or 70.0, minutes)
    else:
        rate = 3.5 + 2.5 * (input.rpe or 5) / 10.0
        metabolic = minutes * rate
        mechanical = _gym_mechanical_kcal(input.exercises)
        epoc = (
            0.12 * (metabolic + mechanical) * ((input.rpe or 5) / 5.0)
            if minutes > 0 or mechanical > 0
            else 0.0
        )
        kcal = (metabolic + mechanical + epoc) * _rest_factor(input.exercises)

    kcal = max(0.0, round(kcal, 1))
    confidence = _confidence(input)
    return KcalEstimate(
        kcal=kcal,
        confidence=confidence,
        confidence_level=_confidence_level(confidence),
        factors=_factors(input),
    )
