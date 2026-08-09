import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED
from app.crud.catalog import exercise_muscle_map


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
