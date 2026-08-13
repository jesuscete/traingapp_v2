"""Seed escalable del catalogo de ejercicios (fuente: free-exercise-db).

Disena la relacion ejercicio <-> musculo de forma relacional:
- `muscle` es el catalogo canonico de musculos. Cada musculo tiene un
  `rollup_code` que lo agrupa en uno de los 12 grupos de fatiga del sistema
  (asi los graficos, la fatiga y el volumen siguen funcionando sin cambios).
- `exercise_muscle` guarda la activacion (0-1) que el ejercicio impone sobre
  cada musculo: los primarios pesan mas que los secundarios, de modo que no
  todos los musculos se fatigan por igual en un ejercicio.

`exercise_catalog.muscle_map` se mantiene como cache desnormalizada (suma de
activaciones agrupadas por rollup) para que las analiticas existentes
(`exercise_muscle_map`, `compute_muscle_impacts`) no cambien.

Este modulo es puro (solo stdlib + `app.analytics.catalog`) para poder
importarse desde las migraciones de alembic sin efectos laterales.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.analytics.catalog import normalize_exercise_name

# (code, label, rollup_code): rollup agrupa en los 12 grupos de fatiga.
MUSCLE_SEED: tuple[tuple[str, str, str], ...] = (
    ("quadriceps", "Cuádriceps", "quadriceps"),
    ("hamstrings", "Isquios", "hamstrings"),
    ("glutes", "Glúteos", "glutes"),
    ("calves", "Gemelos", "calves"),
    ("core", "Core", "core"),
    ("back", "Espalda", "back"),
    ("chest", "Pecho", "chest"),
    ("shoulders", "Hombros", "shoulders"),
    ("biceps", "Bíceps", "biceps"),
    ("triceps", "Tríceps", "triceps"),
    ("forearms", "Antebrazos", "forearms"),
    ("neck", "Cuello", "neck"),
    ("lats", "Dorsales", "back"),
    ("traps", "Trapecios", "back"),
    ("middle_back", "Espalda media", "back"),
    ("lower_back", "Lumbares", "back"),
    ("abdominals", "Abdominales", "core"),
    ("upper_abs", "Abs superiores", "core"),
    ("lower_abs", "Abs inferiores", "core"),
    ("obliques", "Oblicuos", "core"),
    ("adductors", "Aductores", "quadriceps"),
    ("abductors", "Abductores", "glutes"),
)

MUSCLE_ROLLUP: dict[str, str] = {code: rollup for code, _, rollup in MUSCLE_SEED}

# Zonas de agregacion para graficos (radar): agrupan grupos de fatiga.
# La zona "core" agrega abdominales (superiores/inferiores) y oblicuos;
# "back" agrega dorsales, trapecios, espalda media y lumbares.
MUSCLE_ZONES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("legs", "Piernas", ("quadriceps", "hamstrings", "glutes", "calves")),
    ("core", "Core", ("core",)),
    ("back", "Espalda", ("back",)),
    ("chest", "Pecho", ("chest",)),
    ("shoulders", "Hombros", ("shoulders",)),
    ("arms", "Brazos", ("biceps", "triceps", "forearms")),
    ("neck", "Cuello", ("neck",)),
)

MUSCLE_ZONE_LABELS: dict[str, str] = {
    code: label for code, label, _ in MUSCLE_ZONES
}

MUSCLE_ZONE_MEMBERS: dict[str, tuple[str, ...]] = {
    code: members for code, _, members in MUSCLE_ZONES
}

# code (fino o rollup) -> zona.
_MUSCLE_ZONE: dict[str, str] = {
    rollup: zone for zone, _, members in MUSCLE_ZONES for rollup in members
}
for _code, _rollup in MUSCLE_ROLLUP.items():
    _MUSCLE_ZONE[_code] = _MUSCLE_ZONE[_rollup]

MUSCLE_ZONE_OF: dict[str, str] = dict(_MUSCLE_ZONE)


def zone_of(code: str) -> str:
    """Zona de un codigo de musculo (fino o rollup); "other" si es desconocido."""
    return _MUSCLE_ZONE.get(code, "other")


# Musculos del dataset free-exercise-db -> code canonico.
FREE_EXERCISE_DB_MUSCLE_MAP: dict[str, str] = {
    "biceps": "biceps",
    "triceps": "triceps",
    "forearms": "forearms",
    "chest": "chest",
    "shoulders": "shoulders",
    "neck": "neck",
    "quadriceps": "quadriceps",
    "hamstrings": "hamstrings",
    "glutes": "glutes",
    "calves": "calves",
    "abdominals": "abdominals",
    "upper abs": "upper_abs",
    "lower abs": "lower_abs",
    "obliques": "obliques",
    "adductors": "adductors",
    "abductors": "abductors",
    "lats": "lats",
    "traps": "traps",
    "middle back": "middle_back",
    "lower back": "lower_back",
}

# Categorias del dataset tratadas como ejercicios de gimnasio.
GYM_CATEGORIES: frozenset[str] = frozenset(
    {"strength", "plyometrics", "stretching", "powerlifting", "strongman",
     "olympic_weightlifting"}
)

_UNILATERAL_KEYWORDS: tuple[str, ...] = (
    "single arm",
    "single leg",
    "one arm",
    "one leg",
    "single hand",
    "unilateral",
)

_PRIMARY_THRESHOLD = 0.30


def _unilateral(name: str) -> bool:
    return any(keyword in name for keyword in _UNILATERAL_KEYWORDS)


def activation_weights(
    primary: list[str], secondary: list[str]
) -> dict[str, float]:
    """Peso de activacion por musculo canonico (suma == 1.0).

    Los musculos primarios cargan el doble que los secundarios y el total se
    normaliza a 1: asi un ejercicio involucra 1..n musculos sin fatigarlos a
    todos por igual.
    """
    raw: dict[str, float] = {}
    for muscle in primary:
        code = FREE_EXERCISE_DB_MUSCLE_MAP.get(muscle.lower().strip())
        if code:
            raw[code] = raw.get(code, 0.0) + 2.0
    for muscle in secondary:
        code = FREE_EXERCISE_DB_MUSCLE_MAP.get(muscle.lower().strip())
        if code:
            raw[code] = raw.get(code, 0.0) + 1.0
    total = sum(raw.values())
    if total <= 0:
        return {}
    return {code: round(weight / total, 3) for code, weight in raw.items()}


def rollup_muscle_map(weights: dict[str, float]) -> dict[str, float]:
    """Agrupa activaciones por rollup (los 12 grupos de fatiga)."""
    grouped: dict[str, float] = {}
    for code, weight in weights.items():
        rollup = MUSCLE_ROLLUP.get(code, code)
        grouped[rollup] = round(grouped.get(rollup, 0.0) + weight, 3)
    return grouped


def muscle_links_from_map(
    muscle_map: dict[str, float],
) -> list[dict[str, object]]:
    """Convierte un muscle_map (claves = code canonico) en filas de
    `exercise_muscle`. Usado para backfill de los ejercicios curados y para
    materializar las filas relacionales de los ejercicios importados."""
    links: list[dict[str, object]] = []
    for code, activation in muscle_map.items():
        if code not in MUSCLE_ROLLUP:
            continue
        links.append(
            {
                "muscle_code": code,
                "activation": activation,
                "is_primary": activation >= _PRIMARY_THRESHOLD,
            }
        )
    return links


def parse_free_exercise_db(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transforma el dataset en filas listas para insertar en exercise_catalog.

    Cada fila incluye `muscle_map` (cache por rollup) y `muscle_links`
    (filas de exercise_muscle con el code canonico de cada musculo).
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in data:
        category = item.get("category") or ""
        if category not in GYM_CATEGORIES:
            continue
        name = (item.get("name") or "").strip()
        normalized = normalize_exercise_name(name)
        if not name or not normalized or normalized in seen:
            continue
        seen.add(normalized)
        weights = activation_weights(
            item.get("primaryMuscles") or [],
            item.get("secondaryMuscles") or [],
        )
        equipment = item.get("equipment")
        rows.append(
            {
                "id": uuid.uuid4(),
                "name": name,
                "normalized_name": normalized,
                "exercise_type": "gym",
                "uses_bodyweight": equipment == "body only",
                "unilateral": _unilateral(normalized),
                "images": item.get("images") or [],
                "details": {
                    "source": "free_exercise_db",
                    "sourceId": item.get("id"),
                    "category": category,
                    "force": item.get("force"),
                    "level": item.get("level"),
                    "mechanic": item.get("mechanic"),
                    "equipment": equipment,
                    "instructions": item.get("instructions") or [],
                },
                "muscle_map": rollup_muscle_map(weights),
                "muscle_links": muscle_links_from_map(weights),
            }
        )
    return rows


def load_free_exercise_db(path: str | Path) -> list[dict[str, Any]]:
    """Carga y transforma `dist/exercises.json` del dataset free-exercise-db."""
    with open(path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if isinstance(raw, dict) and isinstance(raw.get("exercises"), list):
        raw = raw["exercises"]
    return parse_free_exercise_db(raw)
