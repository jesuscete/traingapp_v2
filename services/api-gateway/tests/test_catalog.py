import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.analytics.catalog_seed import (
    MUSCLE_ROLLUP,
    MUSCLE_SEED,
    MUSCLE_ZONE_LABELS,
    MUSCLE_ZONE_MEMBERS,
    MUSCLE_ZONE_OF,
    zone_of,
)
from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED
from app.crud.catalog import exercise_muscle_map


def _register(client: TestClient, email: str = "muscle@example.com") -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Muscle"},
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_seed_activations_are_valid() -> None:
    for entry in EXERCISE_CATALOG_SEED:
        muscles = entry["muscles"]
        assert isinstance(muscles, dict) and muscles
        total = sum(float(v) for v in muscles.values())
        assert 0 < total <= 1.0
        assert all(0.0 < float(v) <= 1.0 for v in muscles.values())


def test_seed_normalized_names_are_unique() -> None:
    names = [entry["normalized_name"] for entry in EXERCISE_CATALOG_SEED]
    assert len(names) == len(set(names))


def test_exercise_muscle_map_returns_catalog(
    seed_catalog,
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def load() -> dict[str, dict[str, float]]:
        async with db_session_factory() as session:
            return await exercise_muscle_map(session)

    mapping = asyncio.run(load())
    assert "press banca" in mapping
    assert mapping["press banca"]["chest"] == 0.6
    assert "sentadilla" in mapping
    assert mapping["sentadilla"]["quadriceps"] == 0.5


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("press banca", {"chest", "triceps", "shoulders"}),
        ("curl biceps", {"biceps", "forearms"}),
        ("peso muerto", {"glutes", "back", "hamstrings", "quadriceps", "core"}),
    ],
)
def test_seed_entry_muscle_groups(
    entry: str, expected: set[str]
) -> None:
    found = next(
        (e for e in EXERCISE_CATALOG_SEED if e["normalized_name"] == entry),
        None,
    )
    assert found is not None
    assert set(found["muscles"]) == expected


def test_all_muscles_have_zone() -> None:
    for code, _, _ in MUSCLE_SEED:
        assert MUSCLE_ZONE_OF[code] in MUSCLE_ZONE_LABELS


def test_zone_membership_examples() -> None:
    assert MUSCLE_ZONE_OF["abdominals"] == "core"
    assert MUSCLE_ZONE_OF["upper_abs"] == "core"
    assert MUSCLE_ZONE_OF["lower_abs"] == "core"
    assert MUSCLE_ZONE_OF["obliques"] == "core"
    assert MUSCLE_ZONE_OF["lats"] == "back"
    assert MUSCLE_ZONE_OF["traps"] == "back"
    assert MUSCLE_ZONE_OF["middle_back"] == "back"
    assert MUSCLE_ZONE_OF["lower_back"] == "back"
    assert MUSCLE_ZONE_OF["biceps"] == "arms"
    assert MUSCLE_ZONE_OF["triceps"] == "arms"
    assert MUSCLE_ZONE_OF["forearms"] == "arms"
    assert MUSCLE_ZONE_OF["quadriceps"] == "legs"
    assert MUSCLE_ZONE_OF["hamstrings"] == "legs"


def test_zone_of_handles_rollup_codes() -> None:
    assert zone_of("back") == "back"
    assert zone_of("core") == "core"
    assert zone_of("quadriceps") == "legs"
    assert zone_of("desconocido") == "other"


def test_zone_members_are_rollup_groups() -> None:
    all_rollups = set(MUSCLE_ROLLUP.values())
    for members in MUSCLE_ZONE_MEMBERS.values():
        for member in members:
            assert member in all_rollups


def test_list_muscles_endpoint(
    client: TestClient, seed_muscles, db_session_factory
) -> None:
    headers = _register(client)
    response = client.get("/catalog/muscles", headers=headers)
    assert response.status_code == 200
    by_code = {item["code"]: item for item in response.json()}
    assert by_code["abdominals"]["zoneCode"] == "core"
    assert by_code["upper_abs"]["zoneCode"] == "core"
    assert by_code["lats"]["zoneCode"] == "back"
    assert by_code["quadriceps"]["rollupCode"] == "quadriceps"


def test_list_zones_endpoint(
    client: TestClient, seed_muscles, db_session_factory
) -> None:
    headers = _register(client)
    response = client.get("/catalog/zones", headers=headers)
    assert response.status_code == 200
    zones = response.json()
    codes = [zone["code"] for zone in zones]
    assert codes == ["legs", "core", "back", "chest", "shoulders", "arms", "neck"]
    core = next(zone for zone in zones if zone["code"] == "core")
    assert core["label"] == "Core"
    arms = next(zone for zone in zones if zone["code"] == "arms")
    assert arms["members"] == ["biceps", "triceps", "forearms"]


def test_discipline_seed_is_consistent() -> None:
    from app.analytics.discipline_seed import CATEGORY_LABELS, DISCIPLINE_SEED

    codes = [code for _, code, _, _, _ in DISCIPLINE_SEED]
    assert len(codes) == len(set(codes))
    assert "gym" in codes and "other" in codes
    for name, code, met_value, category, kind in DISCIPLINE_SEED:
        assert name.strip()
        assert met_value > 0
        assert category in CATEGORY_LABELS
        assert kind in {"gym", "cardio"}
        assert (kind == "gym") == (code == "gym")


def test_muscle_load_default_matches_discipline_seed() -> None:
    from app.analytics.discipline_seed import DISCIPLINE_SEED
    from app.analytics.fatigue import MUSCLE_LOAD_DEFAULT

    codes = {code for _, code, _, _, _ in DISCIPLINE_SEED}
    assert set(MUSCLE_LOAD_DEFAULT) == codes


def test_session_discipline_literal_matches_seed() -> None:
    from app.analytics.discipline_seed import DISCIPLINE_SEED
    from app.schemas.session import Discipline

    codes = {code for _, code, _, _, _ in DISCIPLINE_SEED}
    assert set(Discipline.__args__) == codes


def test_list_disciplines_endpoint(
    client: TestClient, seed_disciplines, db_session_factory
) -> None:
    headers = _register(client)
    response = client.get("/catalog/disciplines", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 22
    by_code = {item["normalizedName"]: item for item in items}
    gym = by_code["gym"]
    assert gym["category"] == "gimnasio"
    assert gym["kind"] == "gym"
    assert gym["met"] == 5.0
    assert by_code["running"]["category"] == "cardio"
    assert by_code["running"]["kind"] == "cardio"
    running = by_code["running"]
    assert any(
        load["muscleGroup"] == "quadriceps" for load in running["muscleLoads"]
    )
