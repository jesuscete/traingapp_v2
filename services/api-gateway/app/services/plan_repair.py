"""Completa un plan generado hasta cubrir el perfil del deporte (paso determinista post-LLM).

El LLM propone la rutina sin conocer los objetivos del analizador; aquí se mide con el
mismo `analyze` que usa la pantalla "Analizar" y se añaden los patrones que falten, de
modo que una rutina recomendada por la app no puntúe un aprobado raspado.
Puente hasta el generador determinista de M10-F5.
"""

import math
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from app.analytics.sport_analysis import ExerciseWork, SportAnalysis, SportProfile, analyze
from app.schemas.plan import PlanDayOut, PlanExerciseOut, PlanSetTargetOut, PlanSummaryOut
from app.services.sport_analysis import CatalogItem, fits_pattern

TARGET_SCORE = 80
MAX_ADDITIONS = 6
MAX_EXERCISES_PER_DAY = 8
MIN_SETS, MAX_SETS = 2, 4
# Patrones con zona fija (explosivos en fuerza, cuello en resistencia); el resto se
# prescribe en la zona de repeticiones que más le falte al plan.
PATTERN_REPS: dict[str, tuple[int, int]] = {
    "pliometria": (3, 5),
    "olimpico": (3, 5),
    "cuello": (12, 15),
}
ZONE_REPS: dict[str, tuple[int, int]] = {
    "fuerza": (4, 6),
    "hipertrofia": (8, 10),
    "resistencia": (15, 20),
}
PULL_PATTERNS = ("tiron_horizontal", "tiron_vertical")


@dataclass(frozen=True)
class RepairResult:
    plan: PlanSummaryOut
    score_before: int
    score_after: int
    added: list[str]


def plan_work(
    plan: PlanSummaryOut, by_id: dict[uuid.UUID, CatalogItem]
) -> tuple[list[ExerciseWork], set[int]]:
    work: list[ExerciseWork] = []
    sport_days: set[int] = set()
    for day in plan.days:
        if day.day_type == "deporte":
            sport_days.add(day.day_of_week)
            continue
        for ex in day.exercises:
            item = by_id.get(ex.exercise_id) if ex.exercise_id else None
            if item is None:
                continue
            reps = [
                round((s.target_reps_min + s.target_reps_max) / 2)
                if s.target_reps_max
                else s.target_reps_min
                for s in ex.sets
            ]
            work.append(
                ExerciseWork(
                    str(item.row.id),
                    item.name,
                    item.row.muscle_map,
                    item.patterns,
                    reps,
                    day_of_week=day.day_of_week,
                )
            )
    return work, sport_days


def _next_pattern(analysis: SportAnalysis, skipped: set[str]) -> tuple[str, float] | None:
    """Patrón con mayor déficit relativo (los ausentes primero) y series que faltan."""
    candidates = [
        (s.value / s.low, pattern, s.low - s.value)
        for pattern, s in analysis.patterns.items()
        if s.status in ("missing", "low") and pattern not in skipped
    ]
    if not candidates and analysis.balance_status == "low":
        for pattern in PULL_PATTERNS:
            if pattern not in skipped:
                return pattern, float(MIN_SETS + 1)
    if not candidates:
        return None
    _, pattern, deficit = min(candidates)
    return pattern, deficit


def _reps_for(pattern: str, analysis: SportAnalysis) -> tuple[int, int]:
    fixed = PATTERN_REPS.get(pattern)
    if fixed:
        return fixed
    needed = max(
        ZONE_REPS,
        key=lambda z: (
            analysis.rep_zones[z].low - analysis.rep_zones[z].value
            if z in analysis.rep_zones
            else float("-inf")
        ),
    )
    return ZONE_REPS[needed]


def _pick_exercise(
    pattern: str, catalog: Sequence[CatalogItem], used: set[uuid.UUID]
) -> CatalogItem | None:
    pool = [
        c
        for c in catalog
        if pattern in c.patterns
        and fits_pattern(c, pattern)
        and c.row.id not in used
        and c.category not in ("stretching", "cardio")
    ]
    pool.sort(
        key=lambda c: (
            c.row.owner_user_id is not None,  # catálogo común antes que ejercicios propios
            not c.row.images,
            "nameEs" not in (c.row.details or {}),
            (c.row.details or {}).get("level") == "expert",
            c.name,
        )
    )
    return pool[0] if pool else None


def _pick_day(days: list[PlanDayOut]) -> int | None:
    """Día de gimnasio con menos ejercicios (reparte lo añadido entre los días)."""
    gym = [
        (len(d.exercises), i)
        for i, d in enumerate(days)
        if d.day_type == "gimnasio" and len(d.exercises) < MAX_EXERCISES_PER_DAY
    ]
    return min(gym)[1] if gym else None


def complete_plan(
    plan: PlanSummaryOut,
    profile: SportProfile,
    catalog: Sequence[CatalogItem],
    *,
    target: int = TARGET_SCORE,
) -> RepairResult:
    by_id = {c.row.id: c for c in catalog}
    days = [d.model_copy(deep=True) for d in plan.days]
    current = plan.model_copy(update={"days": days})

    work, sport_days = plan_work(current, by_id)
    analysis = analyze(work, profile, weeks=1, sport_days=sport_days)
    before = analysis.score
    used = {ex.exercise_id for d in days for ex in d.exercises if ex.exercise_id}
    skipped: set[str] = set()
    added: list[str] = []

    while analysis.score < target and len(added) < MAX_ADDITIONS:
        choice = _next_pattern(analysis, skipped)
        if choice is None:
            break
        pattern, deficit = choice
        item = _pick_exercise(pattern, catalog, used)
        day_index = _pick_day(days)
        if item is None or day_index is None:
            skipped.add(pattern)
            continue
        low, high = _reps_for(pattern, analysis)
        sets = max(MIN_SETS, min(MAX_SETS, math.ceil(deficit)))
        days[day_index].exercises.append(
            PlanExerciseOut(
                name=item.name,
                exercise_id=item.row.id,
                sets=[
                    PlanSetTargetOut(target_reps_min=low, target_reps_max=high) for _ in range(sets)
                ],
            )
        )
        used.add(item.row.id)
        added.append(item.name)
        work, _ = plan_work(current, by_id)
        new_analysis = analyze(work, profile, weeks=1, sport_days=sport_days)
        if new_analysis.score < analysis.score:
            # No mejora (p. ej. desequilibra zonas): se deshace y se descarta el patrón.
            days[day_index].exercises.pop()
            added.pop()
            skipped.add(pattern)
            continue
        analysis = new_analysis

    return RepairResult(plan=current, score_before=before, score_after=analysis.score, added=added)
