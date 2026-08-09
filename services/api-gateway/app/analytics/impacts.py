from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass

from app.analytics.catalog import muscle_group_of, normalize_exercise_name
from app.models.training import Exercise

_LEGS_FALLBACK = {
    "quadriceps": 0.4,
    "hamstrings": 0.3,
    "glutes": 0.2,
    "calves": 0.1,
}
_ARMS_FALLBACK = {
    "biceps": 0.5,
    "triceps": 0.4,
    "forearms": 0.1,
}


def _fallback_weights(group: str | None) -> dict[str, float]:
    if group == "legs":
        return _LEGS_FALLBACK
    if group == "arms":
        return _ARMS_FALLBACK
    if group is None:
        return {}
    return {group: 1.0}


@dataclass(frozen=True)
class MuscleImpact:
    muscle_group: str
    activation: float


def compute_muscle_impacts(
    exercises: Sequence[Exercise],
    catalog: dict[str, dict[str, float]],
) -> list[MuscleImpact]:
    """Impacto por grupo muscular (0-1, normalizado al grupo mas trabajado).

    Agrega activacion x volumen por ejercicio (catalogo canonico) y
    normaliza por el maximo. Fallback a la heuristica por keywords para
    ejercicios no catalogados.
    """
    totals: dict[str, float] = defaultdict(float)
    for exercise in exercises:
        volume = exercise.volume_kg
        if not volume:
            volume = float(exercise.sets or 0) * float(exercise.reps or 0)
        if not volume:
            volume = 1.0
        weights = catalog.get(normalize_exercise_name(exercise.name))
        if weights is None:
            weights = _fallback_weights(muscle_group_of(exercise.name))
        for group, weight in weights.items():
            totals[group] += weight * volume

    if not totals:
        return []
    max_total = max(totals.values())
    impacts = [
        MuscleImpact(muscle_group=group, activation=round(total / max_total, 3))
        for group, total in totals.items()
    ]
    impacts.sort(key=lambda item: item.activation, reverse=True)
    return impacts
