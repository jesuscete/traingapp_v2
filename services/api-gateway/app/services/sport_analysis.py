"""Carga historial/rutina y catálogo, y ejecuta el análisis de deporte principal (M4)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog import normalize_exercise_name
from app.analytics.patterns import PATTERN_LABELS, exercise_patterns, similarity
from app.analytics.sport_analysis import (
    GROUP_LABELS,
    Basis,
    ExerciseWork,
    SportAnalysis,
    Status,
    analyze,
)
from app.core.config import settings
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.crud import stats as stats_crud
from app.models import ExerciseCatalog, TrainingSession, User
from app.schemas.sport_analysis import (
    AlternativeOut,
    GapOut,
    SportAnalysisOut,
    SuggestionOut,
    TargetStatusOut,
)
from app.services import sport_registry

MIN_HISTORY_SESSIONS = 3
SUGGESTIONS_PER_GAP = 3
ZONE_LABELS = {
    "fuerza": "Fuerza (1-5 reps)",
    "hipertrofia": "Hipertrofia (6-12)",
    "resistencia": "Resistencia (13+)",
}
SPORT_ALIASES = {
    "boxeo": "boxing",
    "boxing": "boxing",
    "kickboxing": "martial_arts",
    "muay thai": "martial_arts",
    "mma": "martial_arts",
    "artes marciales": "martial_arts",
}


def image_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return settings.exercise_image_base_url.rstrip("/") + "/" + path.lstrip("/")


@dataclass(frozen=True)
class CatalogItem:
    row: ExerciseCatalog
    name: str
    patterns: frozenset[str]

    @property
    def category(self) -> str | None:
        return _text(self.row.details or {}, "category")

    @property
    def force(self) -> str | None:
        return _text(self.row.details or {}, "force")

    @property
    def first_image(self) -> str | None:
        return image_url(self.row.images[0]) if self.row.images else None


def _text(details: dict[str, object], key: str) -> str | None:
    value = details.get(key)
    return value if isinstance(value, str) and value else None


def _catalog_item(row: ExerciseCatalog) -> CatalogItem:
    details = row.details or {}
    name_es = _text(details, "nameEs")
    patterns = exercise_patterns(
        row.name,
        row.muscle_map,
        category=_text(details, "category"),
        force=_text(details, "force"),
        name_es=name_es,
    )
    return CatalogItem(row=row, name=name_es or row.name, patterns=patterns)


def main_sport(user: User, requested: str | None) -> str:
    if requested:
        return requested
    for sport in user.sports or []:
        alias = SPORT_ALIASES.get(normalize_exercise_name(str(sport)))
        if alias:
            return alias
    return "boxing"


def _history_work(
    sessions: list[TrainingSession],
    by_id: dict[uuid.UUID, CatalogItem],
    by_name: dict[str, CatalogItem],
) -> list[ExerciseWork]:
    work: list[ExerciseWork] = []
    for ts in sessions:
        for we in ts.workout_exercises:
            item = by_id.get(we.exercise_id) if we.exercise_id else None
            item = item or by_name.get(normalize_exercise_name(we.name))
            if item is None:
                continue
            reps = [
                min((e.reps for e in ws.entries if e.reps), default=None)
                for ws in we.sets
                if not ws.is_warmup
            ]
            work.append(
                ExerciseWork(str(item.row.id), item.name, item.row.muscle_map, item.patterns, reps)
            )
    return work


def _routine_work(
    routine: object, by_id: dict[uuid.UUID, CatalogItem]
) -> tuple[list[ExerciseWork], set[int]]:
    work: list[ExerciseWork] = []
    sport_days: set[int] = set()
    for day in getattr(routine, "days", []):
        if day.day_type == "deporte":
            sport_days.add(day.day_of_week)
        for rex in day.exercises:
            item = by_id.get(rex.exercise_id)
            if item is None:
                continue
            reps = []
            for rs in rex.sets:
                low, high = rs.target_reps_min, rs.target_reps_max
                reps.append(round((low + high) / 2) if low and high else (low or high))
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


# Músculo principal esperado por patrón: descarta coincidencias de nombre engañosas
# (p. ej. "aperturas con rotación" no es potencia rotacional).
PATTERN_MUSCLES: dict[str, frozenset[str]] = {
    "rotacion": frozenset({"core"}),
    "anti_rotacion": frozenset({"core"}),
    "unilateral": frozenset({"quadriceps", "glutes", "hamstrings"}),
    "bisagra": frozenset({"hamstrings", "glutes"}),
    "sentadilla": frozenset({"quadriceps", "glutes"}),
    "cuello": frozenset({"neck"}),
    "tiron_vertical": frozenset({"back"}),
    "tiron_horizontal": frozenset({"back"}),
    "pliometria": frozenset({"quadriceps", "calves", "glutes", "chest", "shoulders"}),
    "olimpico": frozenset({"quadriceps", "glutes", "hamstrings", "back", "shoulders"}),
}


def _fits_pattern(item: CatalogItem, pattern: str) -> bool:
    expected = PATTERN_MUSCLES.get(pattern)
    if expected is None:
        return True
    return any(item.row.muscle_map.get(g, 0) >= 0.5 for g in expected)


def _suggestions(code: str, catalog: list[CatalogItem]) -> list[SuggestionOut]:
    kind, _, key = code.partition(":")
    if kind == "pattern":
        pool = [c for c in catalog if key in c.patterns and _fits_pattern(c, key)]
    elif kind == "balance":
        pool = [c for c in catalog if c.patterns & {"tiron_horizontal", "tiron_vertical"}]
    elif kind == "muscle":
        pool = [c for c in catalog if c.row.muscle_map.get(key, 0) >= 0.5]
    else:
        return []
    pool = [c for c in pool if c.category not in ("stretching", "cardio")]
    pool.sort(
        key=lambda c: (
            c.row.owner_user_id is None and not c.row.images,  # primero con imagen o propios
            "nameEs" not in (c.row.details or {}),
            (c.row.details or {}).get("level") == "expert",
            c.name,
        )
    )
    return [
        SuggestionOut(exercise_id=c.row.id, name=c.name, image_url=c.first_image)
        for c in pool[:SUGGESTIONS_PER_GAP]
    ]


def _targets(statuses: dict[str, Status], labels: dict[str, str]) -> list[TargetStatusOut]:
    return [
        TargetStatusOut(
            key=k, label=labels.get(k, k), value=s.value, low=s.low, high=s.high, status=s.status
        )
        for k, s in statuses.items()
    ]


def to_out(analysis: SportAnalysis, basis: Basis, catalog: list[CatalogItem]) -> SportAnalysisOut:
    return SportAnalysisOut(
        sport=analysis.sport,
        label=analysis.label,
        basis=basis,
        weeks=analysis.weeks,
        score=analysis.score,
        patterns=_targets(analysis.patterns, PATTERN_LABELS),
        muscles=_targets(analysis.muscles, {k: v.capitalize() for k, v in GROUP_LABELS.items()}),
        rep_zones=_targets(analysis.rep_zones, ZONE_LABELS),
        push_sets=analysis.push_sets,
        pull_sets=analysis.pull_sets,
        pull_push_ratio=analysis.pull_push_ratio,
        gaps=[
            GapOut(
                code=g.code,
                severity=g.severity,
                message=g.message,
                suggestions=_suggestions(g.code, catalog),
            )
            for g in analysis.gaps
        ],
    )


async def analyze_user(
    session: AsyncSession,
    user: User,
    *,
    sport: str | None,
    weeks: int,
    basis: str,
) -> SportAnalysisOut:
    profile = sport_registry.sport_profile(main_sport(user, sport))
    rows = await catalog_crud.list_visible(session, user.id)
    catalog = [_catalog_item(r) for r in rows]
    by_id = {c.row.id: c for c in catalog}
    by_name: dict[str, CatalogItem] = {}
    for c in catalog:
        by_name.setdefault(c.row.normalized_name, c)
        by_name.setdefault(normalize_exercise_name(c.name), c)

    sessions = await stats_crud.sessions_in_range(
        session, user.id, datetime.now(UTC) - timedelta(weeks=weeks)
    )
    gym_sessions = [ts for ts in sessions if ts.workout_exercises]
    routine = await routine_crud.get_active_routine(session, user.id)
    routine_work, sport_days = _routine_work(routine, by_id) if routine else ([], set())

    use_history = basis == "historial" or (
        basis == "auto" and len(gym_sessions) >= MIN_HISTORY_SESSIONS
    )
    chosen: Basis
    if use_history:
        work, chosen, span = _history_work(gym_sessions, by_id, by_name), "historial", weeks
    elif routine_work:
        work, chosen, span = routine_work, "rutina", 1
    else:
        work, chosen, span = [], "sin_datos", 1
    result = analyze(work, profile, weeks=span, sport_days=sport_days)
    return to_out(result, chosen, catalog)


async def alternatives(
    session: AsyncSession, user: User, exercise_id: uuid.UUID, *, limit: int
) -> list[AlternativeOut] | None:
    rows = await catalog_crud.list_visible(session, user.id)
    catalog = [_catalog_item(r) for r in rows]
    source = next((c for c in catalog if c.row.id == exercise_id), None)
    if source is None:
        return None
    skip_stretch = source.category != "stretching"
    scored = [
        (
            similarity(
                source.row.muscle_map,
                source.patterns,
                source.force,
                c.row.muscle_map,
                c.patterns,
                c.force,
            ),
            c,
        )
        for c in catalog
        if c.row.id != exercise_id and not (skip_stretch and c.category == "stretching")
    ]
    scored.sort(key=lambda pair: (-pair[0], pair[1].name))
    return [
        AlternativeOut(
            exercise_id=c.row.id,
            name=c.name,
            similarity=score,
            image_url=c.first_image,
            is_custom=c.row.owner_user_id is not None,
        )
        for score, c in scored[:limit]
    ]
