"""Motor determinista de ejercicios: alternativas por condición, prescripción y recomendación."""

import uuid

from fastapi.testclient import TestClient

from app.models import ExerciseCatalog
from app.services import exercise_engine
from app.services.sport_analysis import CatalogItem


def _item(
    name: str,
    patterns: set[str],
    equipment: str,
    muscles: dict[str, float],
    *,
    category: str = "strength",
    curated: bool = False,
) -> CatalogItem:
    row = ExerciseCatalog(
        id=uuid.uuid4(),
        name=name,
        normalized_name=name.lower(),
        exercise_type="gym",
        muscle_map=muscles,
        images=[],
        details=None if curated else {"category": category, "nameEs": name},
    )
    return CatalogItem(row=row, name=name, patterns=frozenset(patterns), equipment=equipment)


CORE = {"core": 0.7, "shoulders": 0.2}
SOURCE = _item("Giro con balón medicinal", {"rotacion", "pliometria"}, "medicine ball", CORE)
CATALOG = [
    SOURCE,
    _item("Leñador en polea", {"rotacion"}, "cable", CORE),
    _item("Giro con mancuerna", {"rotacion"}, "dumbbell", CORE),
    _item("Giro con disco", {"rotacion"}, "other", CORE),
    _item("Slam de balón medicinal", {"pliometria"}, "medicine ball", CORE),
    _item("Rueda abdominal", set(), "other", {"core": 0.8}),
    _item("Estiramiento de tronco", set(), "body only", CORE, category="stretching"),
]


def test_alternatives_keep_the_condition_and_drop_missing_equipment() -> None:
    result = exercise_engine.rank_alternatives(
        SOURCE, CATALOG, exclude_equipment=["medicine ball"], limit=3
    )
    names = [a.item.name for a in result]
    assert set(names) == {"Leñador en polea", "Giro con mancuerna", "Giro con disco"}
    assert all(a.same_condition and "rotacional" in a.reason for a in result)
    assert all(a.item.equipment != "medicine ball" for a in result)


def test_alternatives_show_different_equipment_first() -> None:
    extra = _item("Giro ruso en polea", {"rotacion"}, "cable", CORE)
    result = exercise_engine.rank_alternatives(SOURCE, [*CATALOG, extra], limit=4)
    first_three = [a.item.equipment for a in result[:3]]
    assert len(set(first_three)) == 3


def test_alternatives_fill_with_muscle_similarity_and_mark_it() -> None:
    result = exercise_engine.rank_alternatives(
        SOURCE, CATALOG, exclude_equipment=["medicine ball"], limit=5
    )
    tail = result[3:]
    assert tail and not any(a.same_condition for a in tail)
    assert all(a.item.category != "stretching" for a in result)


def test_alternatives_respect_user_equipment() -> None:
    result = exercise_engine.rank_alternatives(
        SOURCE, CATALOG, allowed=frozenset({"dumbbell", "body only"}), limit=5
    )
    assert [a.item.name for a in result if a.same_condition] == ["Giro con mancuerna"]


def test_isolation_exercise_uses_main_muscle_as_condition() -> None:
    curl = _item("Curl con barra", set(), "barbell", {"biceps": 0.8, "forearms": 0.2})
    hammer = _item("Curl martillo", set(), "dumbbell", {"biceps": 0.6, "forearms": 0.4})
    push = _item("Extensión de tríceps", set(), "cable", {"triceps": 0.9})
    result = exercise_engine.rank_alternatives(curl, [curl, hammer, push], limit=1)
    assert result[0].item.name == "Curl martillo" and "bíceps" in result[0].reason


def test_prescription_by_pattern_focus_and_level() -> None:
    plyo = exercise_engine.prescribe("pliometria", "hipertrofia", "intermediate")
    assert (plyo.reps_min, plyo.reps_max) == (4, 6)
    strength = exercise_engine.prescribe("bisagra", "fuerza", "beginner")
    assert strength.sets == 3 and strength.reps_max == 6
    endurance = exercise_engine.prescribe("rotacion", "resistencia", None)
    assert endurance.rest_seconds == 60


def test_pick_for_pattern_prefers_profile_key_exercises_and_common_ones() -> None:
    weird = _item("Giro exótico", {"rotacion"}, "cable", CORE)
    common = _item("Giro básico", {"rotacion"}, "body only", CORE, curated=True)
    key_low_activation = _item("Giro clave", {"rotacion"}, "other", {"core": 0.3})
    picks = exercise_engine.pick_for_pattern(
        "rotacion", [weird, common, key_low_activation], key_names=["Giro clave"], limit=3
    )
    # Clave del perfil primero (aunque no pase el filtro muscular), luego el básico.
    assert [p.name for p in picks] == ["Giro clave", "Giro básico", "Giro exótico"]


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "Boxer"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_recommend_endpoint_resolves_goal_without_ai(
    client: TestClient, seed_catalog, _block_real_llm: list[str]
) -> None:
    headers = _headers(client, "pegada@example.com")
    response = client.get(
        "/analysis/recommend",
        params={"text": "quiero mejorar mi pegada", "sport": "boxing"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["goalKey"] == "pegada"
    assert data["items"], data
    patterns = {i["pattern"] for i in data["items"]}
    assert patterns & {"rotacion", "pliometria", "olimpico"}
    assert all(i["sets"] >= 2 and i["repsMin"] >= 1 for i in data["items"])
    assert _block_real_llm == []


def test_alternatives_endpoint_filters_missing_equipment(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "alt@example.com")
    items = client.get("/catalog/exercises", headers=headers).json()
    source = next(e for e in items if e["normalizedName"] == "press banca")
    response = client.get(
        f"/catalog/exercises/{source['id']}/alternatives",
        params={"without": ["barbell"], "limit": 5},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    alternatives = response.json()
    assert alternatives and all(a["equipment"] != "barbell" for a in alternatives)
    assert alternatives[0]["reason"].startswith("Mismo patrón")


def test_profile_saves_user_equipment(client: TestClient) -> None:
    headers = _headers(client, "material@example.com")
    body = {"equipment": {"preset": "casa", "extra": [], "missing": ["kettlebells"]}}
    response = client.put("/profile", json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["equipment"] == {
        "preset": "casa",
        "extra": [],
        "missing": ["kettlebells"],
    }
    bad = client.put("/profile", json={"equipment": {"preset": "luna"}}, headers=headers)
    assert bad.status_code == 422
