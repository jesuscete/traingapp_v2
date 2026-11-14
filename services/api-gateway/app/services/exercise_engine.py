"""Motor determinista de ejercicios: alternativas por condición, recomendación por objetivo y
prescripción. Sin IA ni BD: recibe el catálogo ya cargado (`CatalogItem`).

Árbol de decisión de una alternativa:
    ejercicio origen -> patrón principal (el más específico) -> candidatos con ese patrón
    -> fuera el material que falta / no disponible -> orden por patrón + músculos + fuerza.
Si el origen no tiene patrón (aislamiento), la condición es su músculo principal.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from app.analytics.catalog import normalize_exercise_name
from app.analytics.exercise_tags import EQUIPMENT_LABELS, allowed_equipment
from app.analytics.patterns import PATTERN_LABELS, similarity
from app.analytics.sport_analysis import GROUP_LABELS
from app.models import User
from app.services.sport_analysis import CatalogItem, fits_pattern

# Del más específico al más genérico: decide qué patrón es "la condición" de un ejercicio.
PATTERN_SPECIFICITY: tuple[str, ...] = (
    "rotacion",
    "anti_rotacion",
    "cuello",
    "olimpico",
    "pliometria",
    "acarreo",
    "gemelo",
    "bisagra",
    "unilateral",
    "sentadilla",
    "tiron_vertical",
    "tiron_horizontal",
    "empuje_vertical",
    "empuje_horizontal",
)
NON_TRAINING = frozenset({"stretching", "cardio"})
LEVEL_RANK = {"beginner": 0, "intermediate": 1, "expert": 2, "advanced": 2}
PRIMARY_MUSCLE = 0.5


def user_allowed_equipment(user: User) -> frozenset[str] | None:
    data = user.equipment or {}
    preset = data.get("preset")
    extra = data.get("extra") or []
    missing = data.get("missing") or []
    return allowed_equipment(
        preset if isinstance(preset, str) else None,
        [str(e) for e in extra] if isinstance(extra, list) else [],
        [str(e) for e in missing] if isinstance(missing, list) else [],
    )


def main_pattern(patterns: Iterable[str]) -> str | None:
    present = set(patterns)
    return next((p for p in PATTERN_SPECIFICITY if p in present), None)


def main_muscle(muscle_map: Mapping[str, float]) -> str | None:
    if not muscle_map:
        return None
    group, activation = max(muscle_map.items(), key=lambda kv: kv[1])
    return group if activation > 0 else None


def equipment_label(code: str) -> str:
    return EQUIPMENT_LABELS.get(code, code)


def _equipment_ok(
    item: CatalogItem, allowed: frozenset[str] | None, exclude: frozenset[str]
) -> bool:
    if item.equipment in exclude:
        return False
    return allowed is None or item.equipment in allowed


def _level_penalty(item: CatalogItem, user_level: str | None) -> int:
    """0 si el nivel encaja; cuanto mayor, peor (expert para un principiante)."""
    if user_level is None or item.level is None:
        return 0
    return max(0, LEVEL_RANK.get(item.level, 1) - LEVEL_RANK.get(user_level, 1))


_ADVANCED_NAME = re.compile(
    r"\b(lastrad\w*|a una mano|pistol|muscle up|anillas|depth jump|profundidad|"
    r"weighted|one arm|archer)\b"
)


def too_advanced(item: CatalogItem, user_level: str | None) -> bool:
    """Para un principiante: nada de nivel experto ni variantes lastradas/a una mano/pistol."""
    if user_level != "beginner":
        return False
    if item.level == "expert":
        return True
    names = f"{normalize_exercise_name(item.name)} {item.row.normalized_name}"
    return _ADVANCED_NAME.search(names) is not None


def _display_key(item: CatalogItem) -> tuple[bool, bool, str]:
    details = item.row.details or {}
    return (
        not item.row.images,
        "nameEs" not in details and item.row.owner_user_id is None,
        item.name,
    )


@dataclass(frozen=True)
class Alternative:
    item: CatalogItem
    score: float
    reason: str
    same_condition: bool


def rank_alternatives(
    source: CatalogItem,
    catalog: Sequence[CatalogItem],
    *,
    allowed: frozenset[str] | None = None,
    exclude_equipment: Iterable[str] = (),
    user_level: str | None = None,
    limit: int = 8,
) -> list[Alternative]:
    exclude = frozenset(exclude_equipment)
    skip_categories = NON_TRAINING - {source.category or ""}
    pool = [
        c
        for c in catalog
        if c.row.id != source.row.id
        and c.category not in skip_categories
        and _equipment_ok(c, allowed, exclude)
        and not too_advanced(c, user_level)
    ]
    pattern = main_pattern(source.patterns)
    muscle = main_muscle(source.row.muscle_map)

    def condition(c: CatalogItem) -> bool:
        if pattern is not None:
            return pattern in c.patterns and fits_pattern(c, pattern)
        return muscle is not None and c.row.muscle_map.get(muscle, 0) >= PRIMARY_MUSCLE

    def score(c: CatalogItem) -> float:
        return similarity(
            source.row.muscle_map,
            source.patterns,
            source.force,
            c.row.muscle_map,
            c.patterns,
            c.force,
        )

    matching = [c for c in pool if condition(c)]
    matching.sort(key=lambda c: (-score(c), _level_penalty(c, user_level), _display_key(c)))
    matching = diversify_by_equipment(unique_by_name(matching))
    result = [Alternative(c, score(c), _reason(c, pattern, muscle, True), True) for c in matching]
    if len(result) < limit:
        # Sin suficientes del mismo patrón: completar con los más parecidos por músculos.
        seen = {c.row.id for c in matching}
        taken = {normalize_exercise_name(c.name) for c in matching}
        rest = [
            c
            for c in unique_by_name(pool)
            if c.row.id not in seen and normalize_exercise_name(c.name) not in taken
        ]
        rest.sort(key=lambda c: (-score(c), _level_penalty(c, user_level), _display_key(c)))
        result += [
            Alternative(c, score(c), _reason(c, pattern, muscle, False), False)
            for c in rest[: limit - len(result)]
        ]
    return result[:limit]


def unique_by_name(items: Iterable[CatalogItem]) -> list[CatalogItem]:
    """El catálogo puede tener dos filas con el mismo nombre en español: se queda la primera."""
    seen: set[str] = set()
    result: list[CatalogItem] = []
    for item in items:
        key = normalize_exercise_name(item.name)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def diversify_by_equipment(items: Sequence[CatalogItem]) -> list[CatalogItem]:
    """Mantiene el orden pero intercala materiales: el mejor de cada material primero."""
    first: list[CatalogItem] = []
    rest: list[CatalogItem] = []
    seen: set[str] = set()
    for item in items:
        (rest if item.equipment in seen else first).append(item)
        seen.add(item.equipment)
    return first + rest


def _reason(c: CatalogItem, pattern: str | None, muscle: str | None, same: bool) -> str:
    material = equipment_label(c.equipment)
    if same and pattern is not None:
        return f"Mismo patrón: {PATTERN_LABELS[pattern]} · {material}"
    if same and muscle is not None:
        return f"Mismo músculo principal: {GROUP_LABELS.get(muscle, muscle)} · {material}"
    return f"Parecido por músculos · {material}"


# --- Prescripción (series, reps y descanso) ---------------------------------------------


@dataclass(frozen=True)
class Prescription:
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    note: str = ""


FOCUS_PRESCRIPTION: dict[str, Prescription] = {
    "potencia": Prescription(3, 3, 5, 120, "explosivo, máxima velocidad, sin llegar al fallo"),
    "fuerza": Prescription(4, 4, 6, 150, "carga alta, técnica limpia"),
    "hipertrofia": Prescription(3, 8, 12, 90),
    "resistencia": Prescription(3, 12, 15, 60),
}
# Patrones con prescripción propia, sea cual sea el objetivo.
PATTERN_PRESCRIPTION: dict[str, Prescription] = {
    "pliometria": Prescription(
        3, 4, 6, 120, "saltos/lanzamientos explosivos, recuperación completa"
    ),
    "olimpico": Prescription(4, 3, 5, 150, "técnica primero, carga moderada"),
    "cuello": Prescription(3, 12, 15, 60, "controlado, sin tirones"),
    "anti_rotacion": Prescription(3, 8, 12, 60, "lento y controlado (o 20-30 s por lado)"),
    "acarreo": Prescription(3, 20, 30, 90, "pasos (unos 30-40 m) por serie"),
    "gemelo": Prescription(3, 12, 15, 60, "lento y completo; también con rodilla flexionada"),
}
LEVEL_SET_DELTA = {"beginner": -1, "intermediate": 0, "advanced": 0}


def prescribe(pattern: str | None, focus: str, user_level: str | None) -> Prescription:
    base = PATTERN_PRESCRIPTION.get(pattern or "") or FOCUS_PRESCRIPTION.get(
        focus, FOCUS_PRESCRIPTION["hipertrofia"]
    )
    if focus == "potencia" and pattern == "rotacion":
        base = Prescription(3, 5, 8, 90, "explosivo, el giro nace en la cadera")
    if focus == "resistencia" and pattern in ("pliometria", "rotacion"):
        # Resistencia a la potencia: más reps rápidas, menos descanso.
        base = Prescription(3, 8, 12, 60, "rápido y explosivo, descanso corto (como un round)")
    delta = LEVEL_SET_DELTA.get(user_level or "intermediate", 0)
    return Prescription(
        max(2, base.sets + delta), base.reps_min, base.reps_max, base.rest_seconds, base.note
    )


def prescribe_for(
    item: CatalogItem, pattern: str | None, focus: str, user_level: str | None
) -> Prescription:
    """Prescripción ajustada al ejercicio: sin carga no hay «fuerza pesada», el curl nórdico es
    excéntrico y exigente, y las planchas se hacen por tiempo."""
    rx = prescribe(pattern, focus, user_level)
    name = f"{normalize_exercise_name(item.name)} {item.row.normalized_name}"
    if "nordic" in name or "glute ham" in name:
        return Prescription(
            max(2, rx.sets - 1), 3, 6, 120, "excéntrico lento; empieza con ayuda o rango parcial"
        )
    if re.search(r"\b(plancha|plank|bridge|side bridge)\b", name) and pattern == "anti_rotacion":
        return Prescription(rx.sets, 20, 40, 60, "segundos por lado")
    heavy = focus in ("fuerza",) and pattern not in ("pliometria", "olimpico")
    if heavy and item.equipment == "body only":
        return Prescription(
            rx.sets, 8, 15, 90, "sin carga externa: tempo lento o lastre para que cueste"
        )
    return rx


# --- Selección por patrón (recomendador y generador de planes) ----------------------------


def pick_for_pattern(
    pattern: str,
    catalog: Sequence[CatalogItem],
    *,
    key_names: Iterable[str] = (),
    allowed: frozenset[str] | None = None,
    exclude_ids: Iterable[object] = (),
    user_level: str | None = None,
    limit: int = 1,
) -> list[CatalogItem]:
    """Mejores ejercicios para un patrón: primero los clave del perfil, luego por nivel/imagen."""

    keys = [normalize_exercise_name(n) for n in key_names]
    excluded = set(exclude_ids)

    def key_rank(c: CatalogItem) -> int:
        names = {normalize_exercise_name(c.name), c.row.normalized_name}
        return next((i for i, k in enumerate(keys) if k in names), len(keys))

    pool = [
        c
        for c in catalog
        if pattern in c.patterns
        # Los ejercicios clave del perfil ya están elegidos a mano: no se les exige el filtro
        # muscular (los curados reparten la activación y quedarían fuera).
        and (key_rank(c) < len(keys) or fits_pattern(c, pattern))
        and c.category not in NON_TRAINING
        and c.row.id not in excluded
        and _equipment_ok(c, allowed, frozenset())
        and not too_advanced(c, user_level)
    ]
    pool.sort(
        key=lambda c: (
            key_rank(c),
            # En un hueco de fuerza (p. ej. unilateral) mejor no elegir una variante con salto.
            pattern != "pliometria" and "pliometria" in c.patterns,
            not is_common(c),
            _level_penalty(c, user_level),
            c.row.owner_user_id is not None,
            _display_key(c),
        )
    )
    return pool[:limit]


def is_common(item: CatalogItem) -> bool:
    """Ejercicio básico de gimnasio (catálogo curado), preferible a variantes raras."""
    return item.row.owner_user_id is None and not item.row.details
