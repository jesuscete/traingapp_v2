import asyncio
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.food_sources import FoodCandidate
from app.models import Food, User
from app.services.food_import import (
    ImportSource,
    ImportStats,
    implausible_reason,
    save_candidates,
    select_candidates,
)

LIDL = ImportSource("store", "lidl", "Lidl")


def _product(
    code: str, name: str = "Yogur", kcal: float = 60, **extra: object
) -> dict[str, object]:
    return {
        "code": code,
        "product_name": name,
        "brands": ["Lidl", "Milbona"],
        "nutriments": {
            "energy-kcal_100g": kcal,
            "proteins_100g": 4,
            "carbohydrates_100g": 5,
            "fat_100g": 2.5,
        },
        **extra,
    }


def _cand(**values: float) -> FoodCandidate:
    base: dict[str, float] = {
        "kcal_100g": 100,
        "protein_100g": 5,
        "carbs_100g": 15,
        "fat_100g": 2,
    }
    base.update(values)
    return FoodCandidate(source="off", external_id="1", name="x", **base)


def test_source_query_filters_store_or_exact_brand_and_country() -> None:
    assert LIDL.query() == 'stores:"lidl" AND countries_tags:"en:spain"'
    brand = ImportSource("brand", "Optimum Nutrition", "ON", "France")
    assert brand.query() == 'brands_tags:"optimum-nutrition" AND countries_tags:"en:france"'


def test_brand_import_uses_label_and_no_store() -> None:
    source = ImportSource("brand", "hsn", "HSN")
    cands = select_candidates([{**_product("9"), "brands": "hsn"}], source, ImportStats())
    assert (cands[0].brand, cands[0].store) == ("HSN", None)


def test_implausible_reason() -> None:
    assert implausible_reason(_cand()) is None
    assert (
        implausible_reason(_cand(kcal_100g=884, protein_100g=0, carbs_100g=0, fat_100g=100)) is None
    )
    assert implausible_reason(_cand(kcal_100g=1, protein_100g=0, carbs_100g=0, fat_100g=0)) is None
    assert implausible_reason(_cand(kcal_100g=950)) is not None
    assert implausible_reason(_cand(carbs_100g=120)) is not None
    assert implausible_reason(_cand(kcal_100g=200, protein_100g=0, carbs_100g=0, fat_100g=0))
    assert implausible_reason(_cand(kcal_100g=223, protein_100g=30, carbs_100g=10, fat_100g=20))


def test_select_candidates_filters_dedups_and_prefers_sub_brand() -> None:
    stats = ImportStats()
    products = [
        _product("1"),
        _product("1"),  # duplicado
        _product("2", name="Chicle", kcal=156, nutriments=None),  # sin datos
        {**_product("3"), "nutriments": {"energy-kcal_100g": 500, "proteins_100g": 1}},
        {**_product("4"), "brands": "Lidl"},
    ]
    cands = select_candidates(products, LIDL, stats)
    assert [c.external_id for c in cands] == ["1", "4"]
    assert (stats.fetched, stats.no_data, stats.implausible) == (5, 1, 1)
    assert cands[0].store == "Lidl" and cands[0].brand == "Milbona"
    assert cands[1].brand is None  # "Lidl" a secas ya va en store


def test_clean_brand_strips_store_name() -> None:
    from app.services.food_import import clean_brand

    assert clean_brand("AlestoLidl", "Lidl") == "Alesto"
    assert clean_brand("Tastino (Lidl)", "Lidl") == "Tastino"
    assert clean_brand("Lidl", "Lidl") is None
    assert clean_brand("Milbona", "Lidl") == "Milbona"


def test_save_candidates_is_idempotent_and_keeps_user_foods(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async def run() -> None:
        async with db_session_factory() as session:
            user = User(email=f"{uuid.uuid4()}@x.com", hashed_password="x", name="x")
            session.add(user)
            await session.flush()
            session.add_all(
                [
                    Food(source="off", external_id="2", name="Cacheado", kcal_100g=60),
                    Food(
                        source="custom",
                        owner_user_id=user.id,
                        external_id=None,
                        barcode="1",
                        name="Mi yogur",
                        kcal_100g=99,
                    ),
                ]
            )
            await session.commit()

            cands = select_candidates([_product("1"), _product("2")], LIDL, ImportStats())
            first = ImportStats()
            await save_candidates(session, cands, first)
            assert (first.inserted, first.tagged, first.unchanged) == (1, 1, 0)

            again = ImportStats()
            await save_candidates(session, cands, again)
            assert (again.inserted, again.tagged, again.unchanged) == (0, 0, 2)

            total = await session.scalar(select(func.count()).select_from(Food))
            assert total == 3
            mine = await session.scalar(select(Food).where(Food.source == "custom"))
            assert mine is not None and mine.store is None and mine.kcal_100g == 99

    asyncio.run(run())
