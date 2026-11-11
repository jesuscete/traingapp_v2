"""Récords y progresión por ejercicio (funciones puras, sin BD)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

MAX_REPS_FOR_E1RM = 12


@dataclass(frozen=True)
class SetPerformance:
    reps: int | None
    weight_kg: float | None
    is_warmup: bool = False


@dataclass(frozen=True)
class SessionPerformance:
    session_id: str
    performed_at: datetime
    sets: Sequence[SetPerformance]


@dataclass(frozen=True)
class ExerciseRecords:
    max_weight_kg: float | None
    best_e1rm_kg: float | None
    max_reps: int | None
    best_set_volume_kg: float | None
    best_session_volume_kg: float | None


@dataclass(frozen=True)
class ProgressPoint:
    performed_at: datetime
    best_e1rm_kg: float | None
    top_weight_kg: float | None
    volume_kg: float


def estimated_1rm(weight_kg: float | None, reps: int | None) -> float | None:
    """1RM estimado (Epley). Fuera de 1..12 reps la estimación no es fiable."""
    if weight_kg is None or reps is None or weight_kg <= 0:
        return None
    if reps < 1 or reps > MAX_REPS_FOR_E1RM:
        return None
    if reps == 1:
        return round(weight_kg, 1)
    return round(weight_kg * (1 + reps / 30), 1)


def _working(sets: Sequence[SetPerformance]) -> list[SetPerformance]:
    return [s for s in sets if not s.is_warmup]


def _set_volume(s: SetPerformance) -> float:
    if s.reps is None or s.weight_kg is None:
        return 0.0
    return s.reps * s.weight_kg


def _max(values: list[float]) -> float | None:
    return max(values) if values else None


def progress_point(perf: SessionPerformance) -> ProgressPoint:
    working = _working(perf.sets)
    e1rms = [v for s in working if (v := estimated_1rm(s.weight_kg, s.reps)) is not None]
    weights = [s.weight_kg for s in working if s.weight_kg is not None and s.reps]
    return ProgressPoint(
        performed_at=perf.performed_at,
        best_e1rm_kg=_max(e1rms),
        top_weight_kg=_max(weights),
        volume_kg=round(sum(_set_volume(s) for s in working), 1),
    )


def compute_records(history: Sequence[SessionPerformance]) -> ExerciseRecords:
    working = [s for perf in history for s in _working(perf.sets)]
    reps = [s.reps for s in working if s.reps is not None]
    set_volumes = [v for s in working if (v := _set_volume(s)) > 0]
    points = [progress_point(p) for p in history]
    session_volumes = [p.volume_kg for p in points if p.volume_kg > 0]
    return ExerciseRecords(
        max_weight_kg=_max([s.weight_kg for s in working if s.weight_kg is not None and s.reps]),
        best_e1rm_kg=_max([p.best_e1rm_kg for p in points if p.best_e1rm_kg is not None]),
        max_reps=max(reps) if reps else None,
        best_set_volume_kg=_max(set_volumes),
        best_session_volume_kg=_max(session_volumes),
    )
