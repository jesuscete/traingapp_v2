"""El mapa de conocimiento (perfiles + etiquetas de ejercicios) es coherente con el catálogo real.

Se construye el catálogo desde los mismos ficheros que usa el seed (sin BD) para que un
nombre mal escrito en un perfil o en `exercise_tags.json` rompa los tests, no la app.
"""

from functools import lru_cache
from pathlib import Path

import pytest

from app.analytics.catalog import normalize_exercise_name
from app.analytics.catalog_seed import load_free_exercise_db
from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED
from app.analytics.exercise_tags import (
    EQUIPMENT_LABELS,
    allowed_equipment,
    corrected_patterns,
    exercise_equipment,
    infer_equipment,
    load_tags,
)
from app.analytics.patterns import PATTERN_LABELS
from app.analytics.wod_exercise_seed import WOD_EXERCISE_SEED
from app.services import sport_registry

DATA = Path(__file__).resolve().parents[1] / "data"


@lru_cache(maxsize=1)
def _catalog() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = [
        {"key": str(e["normalized_name"]), "names": [str(e["name"])], "details": {}}
        for e in EXERCISE_CATALOG_SEED
    ]
    for row in load_free_exercise_db(DATA / "exercises.json"):
        details = row["details"]
        rows.append(
            {
                "key": row["normalized_name"],
                "names": [row["name"], str(details.get("nameEs") or "")],
                "details": details,
            }
        )
    for wod in WOD_EXERCISE_SEED:
        rows.append(
            {
                "key": normalize_exercise_name(wod["name"]),
                "names": [wod["name"], wod["name_es"]],
                "details": {"category": wod["category"]},
            }
        )
    return rows


def _all_names() -> set[str]:
    return {normalize_exercise_name(n) for r in _catalog() for n in r["names"] if n}  # type: ignore[attr-defined]


def test_every_key_exercise_exists_in_catalog() -> None:
    names = _all_names()
    missing = [
        (doc.sport, pattern, exercise)
        for doc in {d.sport: d for d in sport_registry.load_profiles().values()}.values()
        for pattern, exercises in doc.key_exercises.items()
        for exercise in exercises
        if normalize_exercise_name(exercise) not in names
    ]
    assert missing == []


def test_tags_reference_real_exercises_and_known_vocabulary() -> None:
    keys = {str(r["key"]) for r in _catalog()}
    for key, tag in load_tags().items():
        assert key in keys, key
        if "equipment" in tag:
            assert tag["equipment"] in EQUIPMENT_LABELS, key
        for pattern in tag.get("patterns", []):  # type: ignore[union-attr]
            assert pattern in PATTERN_LABELS, (key, pattern)


def test_every_catalog_exercise_gets_known_equipment() -> None:
    for row in _catalog():
        details = row["details"]
        equipment = exercise_equipment(str(row["key"]), details, row["names"])  # type: ignore[arg-type]
        assert equipment in EQUIPMENT_LABELS, row["key"]


def test_stretches_do_not_count_as_strength_patterns() -> None:
    deduced = frozenset({"cuello", "tiron_vertical"})
    assert corrected_patterns("chin to chest stretch", deduced, "stretching") == frozenset()
    assert corrected_patterns("landmine 180 s", frozenset(), "strength") == {"rotacion"}


@pytest.mark.parametrize(
    ("names", "category", "expected"),
    [
        (["Curl con mancuernas"], None, "dumbbell"),
        (["Jalón en polea alta"], None, "cable"),
        (["Giro ruso con disco"], None, "other"),
        (["Estiramiento de gemelos"], "stretching", "body only"),
        (["Swing con kettlebell"], None, "kettlebells"),
    ],
)
def test_equipment_rules(names: list[str], category: str | None, expected: str) -> None:
    assert infer_equipment(names, category) == expected


def test_user_equipment_presets() -> None:
    assert allowed_equipment(None, [], []) is None
    assert allowed_equipment("gimnasio", [], ["medicine ball"]) == frozenset(EQUIPMENT_LABELS) - {
        "medicine ball"
    }
    home = allowed_equipment("casa", ["other"], [])
    assert home is not None and "dumbbell" in home and "other" in home and "barbell" not in home
    assert allowed_equipment("sin_material", [], []) == {"body only"}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Boxeo", "boxing"),
        ("boxing", "boxing"),
        ("kickboxing", "martial_arts"),
        ("correr", "triathlon"),
        ("Natación", "triathlon"),
        ("tenis", "explosive"),
        ("Fútbol", "explosive"),
        ("baloncesto", "explosive"),
        ("HYROX", "hybrid"),
        ("crossfit", "hybrid"),
        ("golf", None),
        (None, None),
    ],
)
def test_resolve_sport_uses_profile_aliases(raw: str | None, expected: str | None) -> None:
    assert sport_registry.resolve_sport(raw) == expected


def test_goal_map_links_goal_to_patterns() -> None:
    goal = sport_registry.find_goal("boxing", "Quiero mejorar mi pegada en boxeo")
    assert goal is not None and goal.key == "pegada"
    patterns = dict(sport_registry.goal_patterns("boxing", goal))
    assert {"rotacion", "pliometria", "olimpico"} <= set(patterns)
    assert patterns["rotacion"] == 5
    assert sport_registry.find_goal("boxing", "hola, ¿qué tal?") is None


def test_every_profile_quality_with_patterns_has_exercises() -> None:
    """Cada patrón enlazado a una cualidad tiene ejercicios en el catálogo (si no, el árbol
    de decisión se quedaría sin hojas)."""
    from app.analytics.patterns import exercise_patterns

    covered: set[str] = set()
    for row in _catalog():
        details = row["details"]
        names = [n for n in row["names"] if n]  # type: ignore[attr-defined]
        category = details.get("category")  # type: ignore[union-attr]
        deduced = exercise_patterns(names[0], {}, category=category, name_es=" ".join(names[1:]))
        covered |= corrected_patterns(str(row["key"]), deduced, category)
    for doc in sport_registry.load_profiles().values():
        for quality in doc.qualities:
            assert set(quality.patterns) <= covered, (doc.sport, quality.key)


@pytest.mark.parametrize(
    ("sport", "text", "goal"),
    [
        ("boxing", "quiero mejorar mi pegada", "pegada"),
        ("triathlon", "quiero mejorar mi marca en 10k", "rendimiento_carrera"),
        ("triathlon", "quiero subir puertos en bici", "ciclismo"),
        ("triathlon", "me preparo un ironman", "larga_distancia"),
        ("explosive", "quiero saltar mas para machacar", "salto"),
        ("explosive", "quiero ser mas rapido en el sprint", "velocidad"),
        ("explosive", "prevenir lesiones de isquios", "lesiones"),
        ("hybrid", "quiero mejorar en hyrox", "hyrox"),
        ("hybrid", "quiero sacar muscle ups", "gimnasticos"),
        ("hybrid", "mejorar la cargada y la arrancada", "halterofilia"),
    ],
)
def test_each_map_understands_its_goals(sport: str, text: str, goal: str) -> None:
    found = sport_registry.find_goal(sport, text)
    assert found is not None and found.key == goal
    assert sport_registry.goal_patterns(sport, found)


def test_every_sport_map_is_complete() -> None:
    """Cada mapa (salvo el genérico) trae lo que usan los motores: objetivos, ejercicios clave
    para todos sus patrones objetivo, reglas de carga y prevención."""
    docs = {d.sport: d for d in sport_registry.load_profiles().values()}
    assert {"boxing", "triathlon", "explosive", "hybrid", "generic"} <= set(docs)
    for sport, doc in docs.items():
        if sport == "generic":
            continue
        assert len(doc.goals) >= 3, sport
        assert set(doc.pattern_targets) <= set(doc.key_exercises), sport
        assert doc.load_rules and doc.injury_risks, sport
