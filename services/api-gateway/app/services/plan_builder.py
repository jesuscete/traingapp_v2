"""Generador de planes semanal determinista (árbol de decisión, sin IA).

    deporte -> cualidades (prioridad) -> patrones -> ejercicios (material, nivel, variedad)
    días libres -> plantilla de split -> huecos por día (explosivo primero, básicos, apoyo)
    presupuesto de minutos -> series -> relleno de músculos que falten -> prescripción por zona
    reglas de carga: nada de pierna la víspera del deporte si el perfil lo marca.

Devuelve el mismo formato que el generador por LLM (`dayOfWeek`, `dayType`, `exercises`…),
así el resto del flujo (resumen, guardado) no cambia.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import combinations, permutations

from app.analytics.catalog import normalize_exercise_name
from app.analytics.sport_analysis import GROUP_LABELS
from app.schemas.sport_profile import SportProfileDoc
from app.services import exercise_engine
from app.services.sport_analysis import CatalogItem

WARMUP_MINUTES = 10
WORK_MINUTES_PER_SET = 0.75
DEFAULT_SESSION_MINUTES = 60
MAX_EXERCISES_PER_DAY = 7
MAX_FILLS_PER_DAY = 2
MAX_EXPLOSIVE_PER_DAY = 2
HIGH_PRIORITY = 4  # el apoyo de cualidades con prioridad 4-5 entra aunque la sesión esté llena
EXPLOSIVE = ("pliometria", "olimpico", "rotacion")
ACCESSORY_PATTERNS = ("anti_rotacion", "cuello", "acarreo", "gemelo")
LEG_GROUPS = frozenset({"quadriceps", "hamstrings", "glutes", "calves"})
LEG_STRENGTH = frozenset({"sentadilla", "bisagra", "unilateral"})
LEG_LOADING_PATTERNS = frozenset(
    {"pliometria", "olimpico", "gemelo", "sentadilla", "bisagra", "unilateral"}
)


@dataclass(frozen=True)
class DayTemplate:
    kind: str
    label: str
    slots: tuple[str, ...]
    muscles: frozenset[str]
    legs: bool


FULL = DayTemplate(
    "full",
    "Cuerpo completo",
    ("sentadilla", "empuje_horizontal", "tiron_horizontal", "bisagra", "tiron_vertical"),
    frozenset({"chest", "back", "quadriceps", "hamstrings", "glutes", "shoulders", "core"}),
    True,
)
FULL_B = DayTemplate(
    "full",
    "Cuerpo completo",
    ("bisagra", "empuje_vertical", "tiron_vertical", "unilateral", "tiron_horizontal"),
    FULL.muscles,
    True,
)
TORSO = DayTemplate(
    "torso",
    "Torso",
    ("empuje_horizontal", "tiron_horizontal", "empuje_vertical", "tiron_vertical"),
    frozenset({"chest", "back", "shoulders", "biceps", "triceps", "forearms"}),
    False,
)
PIERNA = DayTemplate(
    "pierna",
    "Pierna",
    ("sentadilla", "bisagra", "unilateral"),
    frozenset({"quadriceps", "hamstrings", "glutes", "calves", "core"}),
    True,
)
EMPUJE = DayTemplate(
    "empuje",
    "Empuje",
    ("empuje_horizontal", "empuje_vertical"),
    frozenset({"chest", "shoulders", "triceps"}),
    False,
)
TIRON = DayTemplate(
    "tiron",
    "Tirón",
    ("tiron_vertical", "tiron_horizontal"),
    frozenset({"back", "biceps", "forearms", "neck"}),
    False,
)
SPLIT_NAMES = {
    "fullbody": "Full body",
    "torso_pierna": "Torso / Pierna",
    "upper_lower": "Torso / Pierna",
    "push_pull": "Push / Pull / Pierna",
}


def split_templates(
    count: int, split: str | None, performance: bool
) -> tuple[str, list[DayTemplate]]:
    """Plantilla de días según cuántos días de gimnasio hay y el split elegido."""
    if count <= 0:
        return "", []
    if split == "fullbody" or (
        split in (None, "any") and (count <= 2 or (performance and count == 3))
    ):
        return "Full body", [FULL if i % 2 == 0 else FULL_B for i in range(count)]
    if split in ("torso_pierna", "upper_lower") or (split in (None, "any") and count == 4):
        return "Torso / Pierna", [TORSO if i % 2 == 0 else PIERNA for i in range(count)]
    if split == "push_pull" and count == 2:
        return "Push / Pull", [EMPUJE, TIRON]
    if count == 1:
        return "Full body", [FULL]
    cycle = [EMPUJE, TIRON, PIERNA, TORSO, PIERNA] if count == 5 else [EMPUJE, TIRON, PIERNA]
    days = [cycle[i % len(cycle)] for i in range(count)]
    if count == 7:
        days[-1] = FULL
    return "Push / Pull / Pierna", days


def choose_gym_days(count: int, sport_days: set[int], avoid_eve: bool = False) -> list[int]:
    """Días de gimnasio repartidos por la semana; primero los libres de deporte.

    Orden de preferencia: un día de margen entre sesiones, menos vísperas de deporte (si el
    perfil lo pide), mejor reparto y, a igualdad, los días más tempranos.
    """
    free = [d for d in range(1, 8) if d not in sport_days]
    if count >= len(free):
        extra = [d for d in range(1, 8) if d in sport_days][: count - len(free)]
        return sorted(free + extra)

    def score(days: Sequence[int]) -> tuple[bool, int, int, int]:
        gaps = [(days[(i + 1) % len(days)] - d) % 7 or 7 for i, d in enumerate(days)]
        eves = sum(1 for d in days if (d % 7) + 1 in sport_days) if avoid_eve else 0
        return (min(gaps) < 2, eves, -min(gaps), max(gaps))

    options = [tuple(option) for option in combinations(free, count)]
    ranked = sorted((score(option), option) for option in options)
    return sorted(ranked[0][1])


@dataclass
class _Day:
    weekday: int
    template: DayTemplate
    exercises: list[tuple[CatalogItem, exercise_engine.Prescription, str]] = field(
        default_factory=list
    )
    minutes: float = 0.0


def _minutes(rx: exercise_engine.Prescription) -> float:
    return rx.sets * (WORK_MINUTES_PER_SET + rx.rest_seconds / 60)


def _assign_weekdays(
    templates: list[DayTemplate], weekdays: list[int], sport_days: set[int], avoid_legs: bool
) -> list[tuple[int, DayTemplate]]:
    """Orden de plantillas que minimiza días de pierna la víspera del deporte."""
    if not avoid_legs or len(templates) > 7:
        return list(zip(weekdays, templates, strict=True))

    def cost(order: tuple[DayTemplate, ...]) -> int:
        return sum(
            1
            for day, t in zip(weekdays, order, strict=True)
            if t.legs and (day % 7) + 1 in sport_days
        )

    # Desempate estable (no depende del orden de un set): tipo de día y luego sus huecos.
    best = min(
        set(permutations(templates)), key=lambda o: (cost(o), [(t.kind, t.slots) for t in o])
    )
    assigned = list(zip(weekdays, best, strict=True))
    # Si aún cae pierna la víspera del deporte, ese día pasa a ser de torso (si queda pierna
    # otro día de la semana).
    for index, (day, template) in enumerate(assigned):
        legs_elsewhere = any(t.legs for i, (_, t) in enumerate(assigned) if i != index)
        if template.legs and (day % 7) + 1 in sport_days and legs_elsewhere:
            assigned[index] = (day, TORSO)
    return assigned


@dataclass(frozen=True)
class PlanRequest:
    sports: Sequence[tuple[str, Sequence[int], int | None]]  # nombre, días, minutos
    gym_days: int
    split: str | None
    performance: bool
    level: str | None = None
    allowed: frozenset[str] | None = None
    session_minutes: int = DEFAULT_SESSION_MINUTES


@dataclass
class BuiltPlan:
    split_name: str
    data: dict[str, object]
    notes: list[str]


def build_plan(
    req: PlanRequest, catalog: Sequence[CatalogItem], doc: SportProfileDoc, generic: SportProfileDoc
) -> BuiltPlan:
    sport_days = {d for _, days, _ in req.sports for d in days}
    free_days = 7 - len(sport_days)
    gym_days = min(req.gym_days, free_days)
    split_name, templates = split_templates(gym_days, req.split, req.performance)
    avoid_legs = bool(LEG_GROUPS & set(doc.conflict_groups)) and req.performance
    weekdays = choose_gym_days(len(templates), sport_days, avoid_legs)
    days = [_Day(w, t) for w, t in _assign_weekdays(templates, weekdays, sport_days, avoid_legs)]
    budget = max(20, req.session_minutes - WARMUP_MINUTES)
    global_catalog = [c for c in catalog if c.row.owner_user_id is None]
    focus_of = _pattern_focus(doc)
    priority_of = _pattern_priority(doc)
    used: set[object] = set()

    def key_names(pattern: str) -> list[str]:
        return doc.key_exercises.get(pattern) or generic.key_exercises.get(pattern, [])

    def add(day: _Day, pattern: str, focus: str, *, forced: bool = False) -> bool:
        if len(day.exercises) >= MAX_EXERCISES_PER_DAY:
            return False
        if (
            not forced
            and day.minutes + _minutes(exercise_engine.prescribe(pattern, focus, req.level))
            > budget
        ):
            return False
        day_ids = {item.row.id for item, _, _ in day.exercises}
        day_names = {normalize_exercise_name(item.name) for item, _, _ in day.exercises}
        for exclude in (used | day_ids, day_ids):
            picks = exercise_engine.pick_for_pattern(
                pattern,
                global_catalog,
                key_names=key_names(pattern),
                allowed=req.allowed,
                exclude_ids=exclude,
                user_level=req.level,
                limit=3,
            )
            picks = [p for p in picks if normalize_exercise_name(p.name) not in day_names]
            if picks:
                item = picks[0]
                rx = exercise_engine.prescribe_for(item, pattern, focus, req.level)
                day.exercises.append((item, rx, pattern))
                day.minutes += _minutes(rx)
                used.add(item.row.id)
                return True
        return False

    sport_patterns = _sport_patterns(doc) if req.performance else []
    explosive = [p for p in sport_patterns if p in EXPLOSIVE]
    accessory = [p for p in sport_patterns if p in ACCESSORY_PATTERNS]

    def eve_of_sport(day: _Day) -> bool:
        return avoid_legs and (day.weekday % 7) + 1 in sport_days

    def two_days_before_sport(day: _Day) -> bool:
        return avoid_legs and ((day.weekday + 1) % 7) + 1 in sport_days

    def allowed_on(day: _Day, pattern: str) -> bool:
        """La víspera del deporte: nada que cargue piernas (saltos, olímpicos, gemelo)."""
        return not (eve_of_sport(day) and pattern in LEG_LOADING_PATTERNS)

    # 1) Explosivos al principio de la sesión, repartidos entre los días (rueda).
    for index, pattern in enumerate(explosive * 2):
        for offset in range(len(days)):
            day = days[(index + offset) % len(days)]
            day_patterns = [p for _, _, p in day.exercises]
            if pattern in day_patterns or not allowed_on(day, pattern):
                continue
            if sum(1 for p in day_patterns if p in EXPLOSIVE) >= MAX_EXPLOSIVE_PER_DAY:
                continue
            add(day, pattern, focus_of.get(pattern, "potencia"))
            break
    # 2) Básicos del split: el primero de cada día en zona de fuerza si es rendimiento. Para
    # deportistas, los huecos van en el orden de prioridad del mapa (lo que no quepa es lo menos
    # importante para su deporte).
    for day in days:
        slots = list(day.template.slots)
        if req.performance:
            slots.sort(key=lambda p: -priority_of.get(p, 0))
        for position, pattern in enumerate(slots):
            if pattern in {p for _, _, p in day.exercises}:
                continue
            focus = (
                "fuerza"
                if req.performance and position == 0
                else focus_of.get(pattern, "hipertrofia")
            )
            if focus == "fuerza" and pattern in LEG_STRENGTH and two_days_before_sport(day):
                focus = "hipertrofia"  # pierna pesada a ≥48 h del deporte: aquí, carga moderada
            add(day, pattern, focus if req.performance else "hipertrofia", forced=position == 0)
    # 3) Apoyo del deporte (core anti-rotación, cuello…) donde quede tiempo.
    for index, pattern in enumerate(accessory):
        for offset in range(len(days)):
            day = days[(index + offset) % len(days)]
            if (
                pattern not in {p for _, _, p in day.exercises}
                and allowed_on(day, pattern)
                and add(
                    day,
                    pattern,
                    focus_of.get(pattern, "resistencia"),
                    forced=priority_of.get(pattern, 0) >= HIGH_PRIORITY,
                )
            ):
                break
    notes = _fill_muscles(days, doc, global_catalog, req, budget, used)
    if gym_days < req.gym_days:
        notes.insert(
            0, f"solo quedan {free_days} días libres de deporte, así que van {gym_days} de gimnasio"
        )
    return BuiltPlan(split_name, _to_data(days, req), notes)


def _sport_patterns(doc: SportProfileDoc) -> list[str]:
    """Patrones del deporte por prioridad de su cualidad y luego por series objetivo."""
    priority: dict[str, int] = {}
    for quality in doc.qualities:
        for pattern in quality.patterns:
            priority[pattern] = max(priority.get(pattern, 0), quality.priority)
    patterns = set(priority) | set(doc.pattern_targets)
    return sorted(patterns, key=lambda p: (-priority.get(p, 0), -doc.pattern_targets.get(p, 0), p))


def _pattern_priority(doc: SportProfileDoc) -> dict[str, int]:
    priority: dict[str, int] = {}
    for quality in doc.qualities:
        for pattern in quality.patterns:
            priority[pattern] = max(priority.get(pattern, 0), quality.priority)
    return priority


def _pattern_focus(doc: SportProfileDoc) -> dict[str, str]:
    focus: dict[str, tuple[int, str]] = {}
    for quality in doc.qualities:
        if quality.focus is None:
            continue
        for pattern in quality.patterns:
            if pattern not in focus or quality.priority > focus[pattern][0]:
                focus[pattern] = (quality.priority, quality.focus)
    return {p: f for p, (_, f) in focus.items()}


def _weekly_sets(days: list[_Day]) -> dict[str, float]:
    sets: dict[str, float] = {}
    for day in days:
        for item, rx, _ in day.exercises:
            for group, activation in item.row.muscle_map.items():
                credit = 1.0 if activation >= 0.5 else 0.5 if activation >= 0.25 else 0.0
                sets[group] = sets.get(group, 0.0) + credit * rx.sets
    return sets


def _fill_muscles(
    days: list[_Day],
    doc: SportProfileDoc,
    catalog: Sequence[CatalogItem],
    req: PlanRequest,
    budget: float,
    used: set[object],
) -> list[str]:
    """Rellena con ejercicios de aislamiento los grupos que no llegan a su mínimo semanal."""
    notes: list[str] = []
    weekly = _weekly_sets(days)
    targets = sorted(
        ((g, low) for g, (low, _) in doc.muscle_targets.items() if weekly.get(g, 0.0) < low),
        key=lambda gl: weekly.get(gl[0], 0.0) / gl[1],
    )
    fills = {day.weekday: 0 for day in days}
    for group, low in targets:
        candidates = sorted(
            (
                d
                for d in days
                if group in d.template.muscles and fills[d.weekday] < MAX_FILLS_PER_DAY
            ),
            key=lambda d: d.minutes,
        )
        for day in candidates:
            rx = exercise_engine.prescribe(None, "hipertrofia", req.level)
            if day.minutes + _minutes(rx) > budget or len(day.exercises) >= MAX_EXERCISES_PER_DAY:
                continue
            pool = [
                c
                for c in catalog
                if c.row.muscle_map.get(group, 0) >= 0.5
                and c.category not in exercise_engine.NON_TRAINING
                and c.row.id not in used
                and (req.allowed is None or c.equipment in req.allowed)
            ]
            pool.sort(key=lambda c: (not exercise_engine.is_common(c), bool(c.patterns), c.name))
            if not pool:
                break
            item = pool[0]
            day.exercises.append((item, rx, ""))
            day.minutes += _minutes(rx)
            used.add(item.row.id)
            fills[day.weekday] += 1
            notes.append(
                f"{item.name} para llegar a las series de {GROUP_LABELS.get(group, group)}"
            )
            break
    return notes


def _day_label(day: _Day) -> str:
    patterns = [p for _, _, p in day.exercises]
    if any(p in EXPLOSIVE for p in patterns[:2]):
        return f"{day.template.label} y potencia"
    return day.template.label


def _to_data(days: list[_Day], req: PlanRequest) -> dict[str, object]:
    out: list[dict[str, object]] = []
    gym = {d.weekday: d for d in days}
    sport_of = {d: (name, minutes) for name, sport_days, minutes in req.sports for d in sport_days}
    for weekday in range(1, 8):
        if weekday in gym:
            day = gym[weekday]
            out.append(
                {
                    "dayOfWeek": weekday,
                    "dayType": "gimnasio",
                    "label": _day_label(day),
                    "exercises": [
                        {
                            "name": item.name,
                            "exerciseId": str(item.row.id),
                            "sets": [
                                {
                                    "targetRepsMin": rx.reps_min,
                                    "targetRepsMax": rx.reps_max,
                                    "targetRestSeconds": rx.rest_seconds,
                                }
                                for _ in range(rx.sets)
                            ],
                        }
                        for item, rx, _ in day.exercises
                    ],
                }
            )
        elif weekday in sport_of:
            name, minutes = sport_of[weekday]
            out.append(
                {
                    "dayOfWeek": weekday,
                    "dayType": "deporte",
                    "label": name,
                    "discipline": name,
                    "durationMin": minutes,
                }
            )
        else:
            out.append({"dayOfWeek": weekday, "dayType": "descanso"})
    return {"name": "", "days": out}
