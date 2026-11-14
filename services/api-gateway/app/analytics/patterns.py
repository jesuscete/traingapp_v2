"""Patrones de movimiento de un ejercicio (heurística sobre nombre, categoría y músculos).

Funciones puras: no tocan BD. Sirven al analizador de deporte principal (M4).
"""

import re
from collections.abc import Mapping

from app.analytics.catalog import normalize_exercise_name

PATTERN_LABELS: dict[str, str] = {
    "empuje_horizontal": "Empuje horizontal",
    "empuje_vertical": "Empuje vertical",
    "tiron_horizontal": "Tirón horizontal",
    "tiron_vertical": "Tirón vertical",
    "sentadilla": "Sentadilla",
    "bisagra": "Bisagra de cadera",
    "unilateral": "Pierna unilateral",
    "rotacion": "Potencia rotacional",
    "anti_rotacion": "Core anti-rotación",
    "pliometria": "Pliometría / saltos",
    "olimpico": "Levantamientos explosivos",
    "cuello": "Cuello",
    "acarreo": "Acarreos / agarre",
    "gemelo": "Gemelo y tobillo",
}

PUSH_PATTERNS = frozenset({"empuje_horizontal", "empuje_vertical"})
PULL_PATTERNS = frozenset({"tiron_horizontal", "tiron_vertical"})

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pliometria": (
        "jump",
        "salto",
        "bound",
        "hop",
        "medicine ball throw",
        "slam",
        "lanzamiento",
        "plyo",
        "skater",
        "burpee",
    ),
    "olimpico": (
        "clean",
        "snatch",
        "jerk",
        "push press",
        "cargada",
        "arrancada",
        "empujadora",
        "high pull",
        "kettlebell swing",
        "swing",
    ),
    "rotacion": (
        "twist",
        "woodchop",
        "wood chop",
        "lenador",
        "rotational",
        "rotacion",
        "russian",
        "landmine rotation",
        "side throw",
        "lanzamiento lateral",
    ),
    "anti_rotacion": (
        "pallof",
        "anti rotation",
        "antirrotacion",
        "bird dog",
        "suitcase",
        "plancha lateral",
        "side plank",
    ),
    "cuello": ("neck", "cuello"),
    "gemelo": ("calf", "calves", "gemelo", "talones", "soleo", "heel raise", "pantorrilla"),
    "acarreo": ("farmer", "carry", "paseo del granjero", "suitcase carry", "acarreo"),
    "unilateral": (
        "lunge",
        "zancada",
        "split squat",
        "bulgarian",
        "bulgara",
        "step up",
        "step-up",
        "single leg",
        "una pierna",
        "pistol",
    ),
    "bisagra": (
        "deadlift",
        "peso muerto",
        "hip thrust",
        "good morning",
        "romanian",
        "rumano",
        "glute bridge",
        "puente de gluteo",
        "hyperextension",
        "hiperextension",
        "rdl",
    ),
    "sentadilla": ("squat", "sentadilla", "leg press", "prensa", "hack"),
    "tiron_vertical": ("pulldown", "pull-up", "pullup", "pull up", "chin", "dominada", "jalon"),
    "tiron_horizontal": ("row", "remo", "face pull", "reverse fly", "pajaro"),
    "empuje_vertical": (
        "overhead",
        "military",
        "militar",
        "shoulder press",
        "press de hombro",
        "arnold",
        "landmine press",
        "press landmine",
        "handstand",
    ),
    "empuje_horizontal": (
        "bench",
        "banca",
        "push-up",
        "pushup",
        "push up",
        "flexion",
        "chest press",
        "press de pecho",
        "dip",
        "fondos",
        "fly",
        "aperturas",
    ),
}

PRIMARY_ACTIVATION = 0.5
# Inicio de palabra: "row" no casa con "throw"/"narrow", pero sí admite plurales.
_MATCHERS: dict[str, re.Pattern[str]] = {
    pattern: re.compile(r"\b(?:" + "|".join(re.escape(w) for w in words) + r")")
    for pattern, words in _KEYWORDS.items()
}


def _primary_groups(muscle_map: Mapping[str, float]) -> set[str]:
    return {g for g, a in muscle_map.items() if a >= PRIMARY_ACTIVATION}


def exercise_patterns(
    name: str,
    muscle_map: Mapping[str, float],
    *,
    category: str | None = None,
    force: str | None = None,
    name_es: str | None = None,
) -> frozenset[str]:
    text = " ".join(normalize_exercise_name(n) for n in (name, name_es or "") if n)
    patterns = {p for p, matcher in _MATCHERS.items() if matcher.search(text)}
    primary = _primary_groups(muscle_map)

    if category == "plyometrics":
        patterns.add("pliometria")
    if category == "olympic weightlifting":
        patterns.add("olimpico")
    if "neck" in primary:
        patterns.add("cuello")
    # Sin palabra clave: deducir empuje/tirón por fuerza y músculo dominante.
    if not patterns & (PUSH_PATTERNS | PULL_PATTERNS) and category not in ("stretching", "cardio"):
        if force == "push" and "chest" in primary:
            patterns.add("empuje_horizontal")
        elif force == "push" and "shoulders" in primary:
            patterns.add("empuje_vertical")
        elif force == "pull" and "back" in primary:
            patterns.add("tiron_horizontal")
    if "unilateral" in patterns:
        patterns.discard("sentadilla")
    return frozenset(patterns)


def _cosine(a: Mapping[str, float], b: Mapping[str, float]) -> float:
    dot = sum(a[k] * b.get(k, 0.0) for k in a)
    norm_a = sum(v * v for v in a.values()) ** 0.5
    norm_b = sum(v * v for v in b.values()) ** 0.5
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def similarity(
    source_map: Mapping[str, float],
    source_patterns: frozenset[str],
    source_force: str | None,
    candidate_map: Mapping[str, float],
    candidate_patterns: frozenset[str],
    candidate_force: str | None,
) -> float:
    """0-1: músculos (coseno) + mismo tipo de fuerza + patrones compartidos."""
    union = source_patterns | candidate_patterns
    jaccard = len(source_patterns & candidate_patterns) / len(union) if union else 0.0
    same_force = 1.0 if source_force and source_force == candidate_force else 0.0
    return round(0.7 * _cosine(source_map, candidate_map) + 0.15 * same_force + 0.15 * jaccard, 3)
