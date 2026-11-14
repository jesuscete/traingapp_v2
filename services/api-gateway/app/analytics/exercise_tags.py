"""Mapa de ejercicios: material y patrones corregidos (sin IA).

Fuente de verdad versionada en `data/exercise_tags.json` (correcciones puntuales); lo que no
aparece ahí se deduce con reglas por nombre/categoría. Funciones puras, sin BD.
"""

import json
import re
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path

from app.analytics.catalog import normalize_exercise_name

TAGS_FILE = Path(__file__).resolve().parents[2] / "data" / "exercise_tags.json"

# Vocabulario de material (códigos de free-exercise-db) con su etiqueta en español.
EQUIPMENT_LABELS: dict[str, str] = {
    "barbell": "Barra",
    "e-z curl bar": "Barra Z",
    "dumbbell": "Mancuernas",
    "kettlebells": "Kettlebell",
    "cable": "Polea",
    "machine": "Máquina",
    "bands": "Bandas elásticas",
    "medicine ball": "Balón medicinal",
    "exercise ball": "Fitball",
    "foam roll": "Rodillo",
    "body only": "Peso corporal",
    "other": "Otro material (discos, cajón, comba, trineo…)",
}
BODY_ONLY = "body only"
OTHER = "other"

# Presets de "con qué material entrenas". None = sin restricción (gimnasio completo).
EQUIPMENT_PRESETS: dict[str, frozenset[str] | None] = {
    "gimnasio": None,
    "casa": frozenset(
        {"dumbbell", "kettlebells", "bands", "exercise ball", "foam roll", BODY_ONLY}
    ),
    "sin_material": frozenset({BODY_ONLY}),
}

# Reglas por palabra (nombre en español o inglés ya normalizado), en orden de prioridad.
_EQUIPMENT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("medicine ball", ("balon medicinal", "medicine ball", "wall ball", "slam")),
    ("kettlebells", ("kettlebell",)),
    ("e-z curl bar", ("barra z", "ez bar", "e z")),
    ("dumbbell", ("mancuerna", "dumbbell")),
    ("cable", ("polea", "cable", "pulley")),
    ("machine", ("maquina", "machine", "multipower", "smith", "prensa", "ergometro", "erg ")),
    ("bands", ("banda", "goma", "band")),
    ("exercise ball", ("fitball", "exercise ball", "swiss ball")),
    ("foam roll", ("rodillo", "foam roll", "smr")),
    ("barbell", ("barra", "barbell", "landmine")),
    (OTHER, ("disco", "plate", "comba", "cajon", "trineo", "sled", "saco", "sandbag")),
)
_RULE_MATCHERS = tuple(
    (code, re.compile(r"\b(?:" + "|".join(re.escape(w.strip()) for w in words) + r")"))
    for code, words in _EQUIPMENT_RULES
)
# Sin palabra clave: estas categorías no usan material.
_BODYWEIGHT_CATEGORIES = frozenset({"stretching", "plyometrics", "cardio"})


@lru_cache(maxsize=1)
def load_tags() -> dict[str, dict[str, object]]:
    data = json.loads(TAGS_FILE.read_text(encoding="utf-8"))
    exercises = data.get("exercises", {})
    if not isinstance(exercises, dict):
        raise ValueError(f"{TAGS_FILE}: 'exercises' debe ser un objeto")
    return exercises


def infer_equipment(names: Iterable[str], category: str | None) -> str:
    text = " ".join(normalize_exercise_name(n) for n in names if n) + " "
    for code, matcher in _RULE_MATCHERS:
        if matcher.search(text):
            return code
    if category in _BODYWEIGHT_CATEGORIES:
        return BODY_ONLY
    return OTHER


def exercise_equipment(
    normalized_name: str, details: Mapping[str, object], names: Iterable[str]
) -> str:
    """Material del ejercicio: corrección del mapa > dato del catálogo > reglas."""
    tag = load_tags().get(normalized_name, {})
    tagged = tag.get("equipment")
    if isinstance(tagged, str) and tagged:
        return tagged
    stored = details.get("equipment")
    if isinstance(stored, str) and stored:
        return stored
    category = details.get("category")
    return infer_equipment(names, category if isinstance(category, str) else None)


def corrected_patterns(
    normalized_name: str,
    deduced: frozenset[str],
    category: str | None,
    mechanic: str | None = None,
) -> frozenset[str]:
    """Patrones finales: corrección del mapa > deducidos.

    Los estiramientos no cuentan, y un ejercicio de aislamiento «a una pierna» (gemelo,
    extensión de cuádriceps) no es el patrón de pierna unilateral.
    """
    tag = load_tags().get(normalized_name, {})
    tagged = tag.get("patterns")
    if isinstance(tagged, list):
        return frozenset(str(p) for p in tagged)
    if category == "stretching":
        return frozenset()
    if mechanic == "isolation":
        return deduced - {"unilateral"}
    return deduced


def allowed_equipment(
    preset: str | None, extra: Iterable[str], missing: Iterable[str]
) -> frozenset[str] | None:
    """Material disponible del usuario. None = sin restricción."""
    base = EQUIPMENT_PRESETS.get(preset or "gimnasio")
    missing_set = frozenset(missing)
    if base is None:
        if not missing_set:
            return None
        return frozenset(EQUIPMENT_LABELS) - missing_set
    return (base | frozenset(extra)) - missing_set
