from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.analytics.catalog import muscle_group_of, normalize_exercise_name
from app.analytics.catalog_seed import zone_of


class VolumeExercise(Protocol):
    """Lo minimo que necesita el calculo de impactos (legacy o gym)."""

    @property
    def name(self) -> str: ...

    @property
    def volume_kg(self) -> float: ...

    @property
    def sets(self) -> int | None: ...

    @property
    def reps(self) -> int | None: ...


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

# Perfil muscular por disciplina (cardio/deportes) cuando no hay ejercicios
# catalogados ni heuristica por keywords. Regla determinista (ADR-0xx).
DISCIPLINE_MUSCLE_PROFILES: dict[str, dict[str, float]] = {
    "running": {
        "quadriceps": 1.0,
        "glutes": 0.9,
        "hamstrings": 0.8,
        "calves": 0.8,
        "core": 0.4,
    },
    "cycling": {
        "quadriceps": 1.0,
        "glutes": 0.6,
        "hamstrings": 0.5,
        "calves": 0.5,
        "core": 0.4,
    },
    "swimming": {
        "back": 1.0,
        "shoulders": 1.0,
        "core": 0.9,
        "chest": 0.8,
        "triceps": 0.7,
        "quadriceps": 0.6,
    },
    "boxing": {
        "shoulders": 1.0,
        "core": 0.9,
        "triceps": 0.7,
        "biceps": 0.6,
        "back": 0.5,
        "forearms": 0.5,
        "chest": 0.4,
    },
    "climbing": {
        "forearms": 1.0,
        "back": 0.9,
        "biceps": 0.8,
        "shoulders": 0.7,
        "core": 0.6,
    },
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
    zone: str = "other"


def compute_muscle_impacts(
    exercises: Sequence[VolumeExercise],
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
        MuscleImpact(
            muscle_group=group,
            activation=round(total / max_total, 3),
            zone=zone_of(group),
        )
        for group, total in totals.items()
    ]
    impacts.sort(key=lambda item: item.activation, reverse=True)
    return impacts


def compute_discipline_impacts(
    discipline: str, profile: dict[str, float] | None = None
) -> list[MuscleImpact]:
    """Impacto muscular de un deporte (cardio) sin ejercicios catalogados.

    Usa el perfil normalizado (0-1) del catalogo si se proporciona; si no,
    cae al perfil determinista interno de la disciplina. Devuelve el perfil
    normalizado al grupo mas trabajado (0-1). Vacio si no hay perfil.
    """
    muscle_map = profile if profile is not None else DISCIPLINE_MUSCLE_PROFILES.get(discipline)
    if not muscle_map:
        return []
    max_weight = max(muscle_map.values())
    impacts = [
        MuscleImpact(
            muscle_group=group,
            activation=round(weight / max_weight, 3),
            zone=zone_of(group),
        )
        for group, weight in muscle_map.items()
    ]
    impacts.sort(key=lambda item: item.activation, reverse=True)
    return impacts
