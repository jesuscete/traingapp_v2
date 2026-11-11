"""Análisis del entrenamiento frente a las demandas del deporte principal (RF-03/RF-04).

Determinista y puro: calcula carencias y desequilibrios. El LLM solo redacta a partir
de este resultado.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.analytics.patterns import PATTERN_LABELS, PULL_PATTERNS, PUSH_PATTERNS

PRIMARY = 0.5
SECONDARY = 0.25
HEAVY_DAY_SETS = 6
RepZone = str  # "fuerza" (1-5) | "hipertrofia" (6-12) | "resistencia" (13+)
StatusValue = Literal["missing", "low", "ok", "high"]
Severity = Literal["alta", "media", "baja"]
Basis = Literal["historial", "rutina", "sin_datos"]


@dataclass(frozen=True)
class SportProfile:
    sport: str
    label: str
    pattern_targets: Mapping[str, float]  # series semanales mínimas por patrón
    muscle_targets: Mapping[str, tuple[float, float]]  # rango de series semanales
    rep_zones: Mapping[RepZone, tuple[float, float]]  # rango de proporción de series
    min_pull_push_ratio: float
    conflict_groups: frozenset[str]  # grupos que no conviene machacar la víspera


BOXING = SportProfile(
    sport="boxing",
    label="Boxeo",
    pattern_targets={
        "rotacion": 6,
        "anti_rotacion": 4,
        "pliometria": 6,
        "olimpico": 3,
        "unilateral": 6,
        "bisagra": 4,
        "cuello": 4,
        "tiron_horizontal": 6,
        "tiron_vertical": 4,
    },
    muscle_targets={
        "shoulders": (6, 12),
        "core": (8, 16),
        "back": (10, 18),
        "glutes": (8, 14),
        "quadriceps": (8, 14),
        "hamstrings": (6, 12),
        "calves": (6, 12),
        "chest": (6, 12),
        "neck": (3, 8),
        "forearms": (3, 8),
    },
    rep_zones={"fuerza": (0.30, 0.55), "hipertrofia": (0.30, 0.55), "resistencia": (0.05, 0.25)},
    min_pull_push_ratio=1.0,
    conflict_groups=frozenset({"shoulders", "quadriceps", "hamstrings", "glutes", "calves"}),
)

GENERIC = SportProfile(
    sport="generic",
    label="Rendimiento general",
    pattern_targets={
        "empuje_horizontal": 4,
        "tiron_horizontal": 4,
        "sentadilla": 4,
        "bisagra": 4,
        "anti_rotacion": 2,
    },
    muscle_targets={
        "back": (8, 18),
        "chest": (6, 16),
        "quadriceps": (8, 16),
        "hamstrings": (6, 14),
        "glutes": (6, 14),
        "core": (6, 14),
    },
    rep_zones={"fuerza": (0.15, 0.45), "hipertrofia": (0.40, 0.75), "resistencia": (0.0, 0.30)},
    min_pull_push_ratio=0.9,
    conflict_groups=frozenset({"quadriceps", "hamstrings", "glutes"}),
)

PROFILES: dict[str, SportProfile] = {"boxing": BOXING, "martial_arts": BOXING}


def profile_for(sport: str | None) -> SportProfile:
    return PROFILES.get(sport or "", GENERIC)


@dataclass(frozen=True)
class ExerciseWork:
    """Un ejercicio con sus series de trabajo (reps reales o reps objetivo)."""

    exercise_id: str | None
    name: str
    muscle_map: Mapping[str, float]
    patterns: frozenset[str]
    reps: Sequence[int | None]
    day_of_week: int | None = None


@dataclass(frozen=True)
class Gap:
    code: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class Status:
    value: float
    low: float
    high: float | None
    status: StatusValue


@dataclass
class SportAnalysis:
    sport: str
    label: str
    weeks: float
    score: int
    patterns: dict[str, Status]
    muscles: dict[str, Status]
    rep_zones: dict[str, Status]
    push_sets: float
    pull_sets: float
    pull_push_ratio: float | None
    balance_status: str
    conflicts: list[str]
    gaps: list["Gap"] = field(default_factory=list)


def rep_zone(reps: int) -> RepZone:
    if reps <= 5:
        return "fuerza"
    if reps <= 12:
        return "hipertrofia"
    return "resistencia"


def _status(value: float, low: float, high: float | None) -> Status:
    state: StatusValue
    if value <= 0 and low > 0:
        state = "missing"
    elif value < low:
        state = "low"
    elif high is not None and value > high:
        state = "high"
    else:
        state = "ok"
    return Status(round(value, 1), low, high, state)


def _conflicts(
    work: Sequence[ExerciseWork], profile: SportProfile, sport_days: set[int]
) -> list[str]:
    day_load: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for ex in work:
        if ex.day_of_week is None:
            continue
        for group, activation in ex.muscle_map.items():
            if activation >= PRIMARY and group in profile.conflict_groups:
                day_load[ex.day_of_week][group] += len(ex.reps)
    messages: list[str] = []
    for day, loads in sorted(day_load.items()):
        heavy = sorted(g for g, sets in loads.items() if sets >= HEAVY_DAY_SETS)
        next_day = day % 7 + 1
        if heavy and next_day in sport_days:
            messages.append(f"{day}->{next_day}:" + ",".join(heavy))
        if heavy and day in sport_days:
            messages.append(f"{day}={day}:" + ",".join(heavy))
    return messages


def analyze(
    work: Sequence[ExerciseWork],
    profile: SportProfile,
    *,
    weeks: float,
    sport_days: set[int] | None = None,
) -> SportAnalysis:
    weeks = max(weeks, 1e-6)
    muscle_sets: dict[str, float] = defaultdict(float)
    pattern_sets: dict[str, float] = defaultdict(float)
    zone_counts: dict[str, int] = defaultdict(int)
    push = pull = 0.0
    for ex in work:
        n = len(ex.reps)
        for group, activation in ex.muscle_map.items():
            if activation >= PRIMARY:
                muscle_sets[group] += n
            elif activation >= SECONDARY:
                muscle_sets[group] += 0.5 * n
        for pattern in ex.patterns:
            pattern_sets[pattern] += n
        if ex.patterns & PUSH_PATTERNS:
            push += n
        if ex.patterns & PULL_PATTERNS:
            pull += n
        for reps in ex.reps:
            if reps is not None and reps > 0:
                zone_counts[rep_zone(reps)] += 1

    patterns = {
        p: _status(pattern_sets[p] / weeks, target, None)
        for p, target in profile.pattern_targets.items()
    }
    muscles = {
        g: _status(muscle_sets[g] / weeks, low, high)
        for g, (low, high) in profile.muscle_targets.items()
    }
    total_sets = sum(zone_counts.values())
    rep_zones = {
        z: _status(zone_counts[z] / total_sets if total_sets else 0.0, low, high)
        for z, (low, high) in profile.rep_zones.items()
    }
    ratio = round(pull / push, 2) if push else None
    if push == 0 and pull == 0:
        balance = "missing"
    elif ratio is not None and ratio < profile.min_pull_push_ratio:
        balance = "low"
    else:
        balance = "ok"

    pattern_cov = [min(1.0, s.value / s.low) for s in patterns.values()] or [1.0]
    muscle_ok = [
        1.0 if s.status == "ok" else 0.5 if s.status in ("low", "high") else 0.0
        for s in muscles.values()
    ] or [1.0]
    zone_ok = [1.0 if s.status == "ok" else 0.0 for s in rep_zones.values()] or [1.0]
    score = round(
        100
        * (
            0.5 * sum(pattern_cov) / len(pattern_cov)
            + 0.3 * sum(muscle_ok) / len(muscle_ok)
            + 0.1 * sum(zone_ok) / len(zone_ok)
            + 0.1 * (1.0 if balance == "ok" else 0.0)
        )
    )
    analysis = SportAnalysis(
        sport=profile.sport,
        label=profile.label,
        weeks=round(weeks, 2),
        score=score,
        patterns=patterns,
        muscles=muscles,
        rep_zones=rep_zones,
        push_sets=round(push / weeks, 1),
        pull_sets=round(pull / weeks, 1),
        pull_push_ratio=ratio,
        balance_status=balance,
        conflicts=_conflicts(work, profile, sport_days or set()),
    )
    analysis.gaps = _gaps(analysis)
    return analysis


GROUP_LABELS = {
    "quadriceps": "cuádriceps",
    "hamstrings": "isquiotibiales",
    "glutes": "glúteos",
    "calves": "gemelos",
    "core": "core",
    "back": "espalda",
    "chest": "pecho",
    "shoulders": "hombros",
    "biceps": "bíceps",
    "triceps": "tríceps",
    "forearms": "antebrazos",
    "neck": "cuello",
}


def _groups_es(groups: str) -> str:
    return ", ".join(GROUP_LABELS.get(g, g) for g in groups.split(","))


DAY_NAMES = {
    1: "lunes",
    2: "martes",
    3: "miércoles",
    4: "jueves",
    5: "viernes",
    6: "sábado",
    7: "domingo",
}


def _pattern_gaps(a: SportAnalysis) -> list[Gap]:
    gaps: list[Gap] = []
    for pattern, s in a.patterns.items():
        if s.status in ("missing", "low"):
            label = PATTERN_LABELS.get(pattern, pattern)
            gaps.append(
                Gap(
                    code=f"pattern:{pattern}",
                    severity="alta" if s.status == "missing" else "media",
                    message=f"{label}: {s.value:g} series/semana (objetivo ≥ {s.low:g}).",
                )
            )
    return gaps


def _muscle_gaps(a: SportAnalysis) -> list[Gap]:
    gaps: list[Gap] = []
    for group, s in a.muscles.items():
        label = GROUP_LABELS.get(group, group).capitalize()
        if s.status in ("missing", "low"):
            gaps.append(
                Gap(
                    code=f"muscle:{group}",
                    severity="media" if s.status == "missing" else "baja",
                    message=f"{label}: {s.value:g} series/semana (rango {s.low:g}-{s.high:g}).",
                )
            )
        elif s.status == "high":
            gaps.append(
                Gap(
                    code=f"muscle_high:{group}",
                    severity="baja",
                    message=f"{label}: {s.value:g} series/semana, por encima de {s.high:g}.",
                )
            )
    return gaps


def _other_gaps(a: SportAnalysis) -> list[Gap]:
    gaps: list[Gap] = []
    if a.balance_status == "low" and a.pull_push_ratio is not None:
        gaps.append(
            Gap(
                code="balance:pull_push",
                severity="media",
                message=(
                    f"Más empuje que tirón ({a.push_sets:g} vs {a.pull_sets:g} series/semana). "
                    "El golpeo ya carga el empuje: compensa con tirones."
                ),
            )
        )
    for zone, s in a.rep_zones.items():
        if s.status != "ok":
            gaps.append(
                Gap(
                    code=f"reps:{zone}",
                    severity="baja",
                    message=(
                        f"Series en zona {zone}: {s.value:.0%} "
                        f"(recomendado {s.low:.0%}-{(s.high or 1):.0%})."
                    ),
                )
            )
    for conflict in a.conflicts:
        days, groups = conflict.split(":")
        if "->" in days:
            gym, sport = (int(d) for d in days.split("->"))
            text = (
                f"El {DAY_NAMES[gym]} cargas {_groups_es(groups)} "
                f"y el {DAY_NAMES[sport]} toca deporte."
            )
        else:
            day = int(days.split("=")[0])
            text = (
                f"El {DAY_NAMES[day]} coinciden gimnasio pesado de {_groups_es(groups)} y deporte."
            )
        gaps.append(Gap(code=f"conflict:{days}", severity="media", message=text))
    return gaps


def _gaps(a: SportAnalysis) -> list[Gap]:
    order = {"alta": 0, "media": 1, "baja": 2}
    gaps = _pattern_gaps(a) + _other_gaps(a) + _muscle_gaps(a)
    return sorted(gaps, key=lambda g: order[g.severity])
