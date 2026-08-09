"""Reglas de negocio de volumen/tonelaje para entrenos de gimnasio (ADR-0xx).

Solo gimnasio. Deportes quedan fuera.
- Una serie normal tiene exactamente 1 set_entry; un dropset 2+ ordenados por
  entry_order (sin descanso entre tramos).
- Volumen excluye las series is_warmup = true.
- Si el ejercicio usa bodyweight, el volumen suma el peso corporal del usuario
  al peso anadido en cada set_entry.
- El peso se normaliza siempre a kg (lb -> kg); weight_unit queda como
  preferencia de visualizacion.
- Isometricos (sin reps) no generan tonelaje.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.analytics.catalog import normalize_exercise_name

LB_TO_KG = 0.45359237


@dataclass(frozen=True)
class ExerciseVolume:
    volume_kg: float
    set_volumes: tuple[float, ...]


@dataclass(frozen=True)
class SummaryResult:
    total_volume: float
    avg_rpe: float | None
    sets_count: int


def normalize_weight(weight: float | None, unit: str | None) -> float | None:
    if weight is None:
        return None
    if (unit or "kg").lower() == "lb":
        return weight * LB_TO_KG
    return float(weight)


def _entry_volume(
    entry: object,
    *,
    user_weight_kg: float | None,
    uses_bodyweight: bool,
) -> float:
    reps = getattr(entry, "reps", None)
    if not isinstance(reps, (int, float)) or reps < 1:
        return 0.0
    weight = normalize_weight(getattr(entry, "weight", None), getattr(entry, "weight_unit", None))
    if weight is None:
        weight = 0.0
    effective = weight
    if uses_bodyweight and user_weight_kg:
        effective += user_weight_kg
    return effective * float(reps)


def compute_exercise_volume(
    exercise: object,
    *,
    user_weight_kg: float | None,
    uses_bodyweight: bool,
) -> ExerciseVolume:
    """Volumen de un workout_exercise (suma de series; excluye warmups)."""
    set_volumes: list[float] = []
    for ws in getattr(exercise, "sets", ()):
        if getattr(ws, "is_warmup", False):
            set_volumes.append(0.0)
            continue
        set_volumes.append(
            sum(
                _entry_volume(entry, user_weight_kg=user_weight_kg, uses_bodyweight=uses_bodyweight)
                for entry in getattr(ws, "entries", ())
            )
        )
    return ExerciseVolume(volume_kg=sum(set_volumes), set_volumes=tuple(set_volumes))


def compute_summary(
    exercises: Sequence[object],
    *,
    user_weight_kg: float | None,
    uses_bodyweight_map: dict[str, bool],
) -> SummaryResult:
    """Resumen del entreno: volumen total (sin warmups), RPE medio y nº de series.

    `uses_bodyweight_map` indexa por normalized_name del ejercicio.
    """
    total = 0.0
    sets_count = 0
    rpes: list[float] = []
    for exercise in exercises:
        uses_bw = uses_bodyweight_map.get(
            normalize_exercise_name(getattr(exercise, "name", "")), False
        )
        volume = compute_exercise_volume(
            exercise, user_weight_kg=user_weight_kg, uses_bodyweight=uses_bw
        )
        total += volume.volume_kg
        for ws in getattr(exercise, "sets", ()):
            if not getattr(ws, "is_warmup", False):
                sets_count += 1
            for entry in getattr(ws, "entries", ()):
                rpe = getattr(entry, "rpe", None)
                if isinstance(rpe, (int, float)):
                    rpes.append(float(rpe))
    avg_rpe = round(sum(rpes) / len(rpes), 2) if rpes else None
    return SummaryResult(total_volume=round(total, 2), avg_rpe=avg_rpe, sets_count=sets_count)


@dataclass(frozen=True)
class FlatExercise:
    """Proyeccion ligera de un workout_exercise para analiticas compartidas.

    Permite reutilizar `compute_volume` / `compute_muscle_impacts` con la
    estructura antigua sin recalcular nada: el volumen ya esta materializado
    en `volume_kg` y el peso/reps provienen del tramo mas pesado (carga
    anadida, normalizada a kg).
    """

    name: str
    volume_kg: float
    weight_kg: float | None
    reps: int | None
    sets: int


def flatten_workout_exercises(
    workout_exercises: Sequence[object],
) -> list[FlatExercise]:
    """Aplana la jerarquia a un item por ejercicio (peso/reps del tramo mas pesado)."""
    result: list[FlatExercise] = []
    for exercise in workout_exercises:
        best_weight: float | None = None
        best_reps: int | None = None
        working_sets = 0
        for ws in getattr(exercise, "sets", ()):
            if getattr(ws, "is_warmup", False):
                continue
            working_sets += 1
            for entry in getattr(ws, "entries", ()):
                reps = getattr(entry, "reps", None)
                if not isinstance(reps, (int, float)) or reps < 1:
                    continue
                weight = normalize_weight(
                    getattr(entry, "weight", None), getattr(entry, "weight_unit", None)
                )
                if weight is None:
                    weight = 0.0
                if best_weight is None or weight > best_weight:
                    best_weight = weight
                    best_reps = int(reps)
        result.append(
            FlatExercise(
                name=getattr(exercise, "name", ""),
                volume_kg=float(getattr(exercise, "volume_kg", 0.0) or 0.0),
                weight_kg=best_weight,
                reps=best_reps,
                sets=working_sets,
            )
        )
    return result
