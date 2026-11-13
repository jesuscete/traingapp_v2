from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.food_sources import FoodCandidate, FoodSourceError

TODAY = datetime.now(UTC).date().isoformat()
LABEL = {
    "name": "Crema de cacahuete Marca X",
    "kcal100g": 600,
    "protein100g": 25,
    "carbs100g": 15,
    "fat100g": 48,
    "servings": [{"label": "1 cucharada", "grams": 16}],
}


def _headers(client: TestClient, email: str, profile: bool = True) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "N"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    if profile:
        client.put(
            "/profile",
            json={"weightKg": 75, "heightCm": 178, "birthYear": 1994, "sex": "male"},
            headers=headers,
        )
    return headers


def _food(
    client: TestClient, headers: dict[str, str], body: dict[str, Any] = LABEL
) -> dict[str, Any]:
    response = client.post("/nutrition/foods", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _entry(client: TestClient, headers: dict[str, str], **body: Any) -> Any:
    return client.post(
        "/nutrition/meals", json={"eatenOn": TODAY, "meal": "desayuno", **body}, headers=headers
    )


def test_exact_and_estimated_entries(client: TestClient) -> None:
    headers = _headers(client, "meals@example.com")
    food = _food(client, headers)
    assert food["isCustom"] is True

    weighed = _entry(client, headers, foodId=food["id"], grams=37)
    assert weighed.status_code == 201, weighed.text
    assert (weighed.json()["kcal"], weighed.json()["method"]) == (222.0, "etiqueta")
    serving = _entry(client, headers, foodId=food["id"], servings=2).json()
    assert (serving["grams"], serving["method"]) == (32.0, "racion")
    quick = _entry(client, headers, name="Menú del día", kcal=650, meal="comida").json()
    assert quick["method"] == "rapida"

    day = client.get("/nutrition/day", headers=headers).json()
    assert day["totals"]["kcal"] == 222 + 192 + 650
    assert day["exactKcal"] == 222 and day["estimatedKcal"] == 192 + 650
    assert len(day["meals"]["desayuno"]) == 2 and len(day["meals"]["comida"]) == 1

    # Corrijo con la báscula: la ración pasa a ser exacta.
    fixed = client.put(f"/nutrition/meals/{serving['id']}", json={"grams": 30}, headers=headers)
    assert fixed.json()["method"] == "pesada" and fixed.json()["kcal"] == 180


def test_whole_day_entry(client: TestClient) -> None:
    headers = _headers(client, "whole-day@example.com")
    entry = _entry(
        client,
        headers,
        name="Registro del día",
        kcal=2300,
        proteinG=160,
        carbsG=250,
        fatG=70,
        meal="dia",
    )
    assert entry.status_code == 201, entry.text
    day = client.get("/nutrition/day", headers=headers).json()
    assert len(day["meals"]["dia"]) == 1
    assert day["totals"]["kcal"] == 2300 and day["totals"]["proteinG"] == 160


def test_entry_validation_and_isolation(client: TestClient) -> None:
    owner = _headers(client, "owner-food@example.com")
    other = _headers(client, "other-food@example.com")
    food = _food(client, owner)
    assert _entry(client, owner, foodId=food["id"]).status_code == 422  # sin gramos ni raciones
    assert _entry(client, owner, foodId=food["id"], grams=10, servings=1).status_code == 422
    assert _entry(client, owner, name="x").status_code == 422  # rápido sin kcal
    assert _entry(client, other, foodId=food["id"], grams=10).status_code == 422  # ajeno
    entry = _entry(client, owner, foodId=food["id"], grams=10).json()
    assert client.delete(f"/nutrition/meals/{entry['id']}", headers=other).status_code == 404
    assert client.delete(f"/nutrition/meals/{entry['id']}", headers=owner).status_code == 204


def test_target_includes_training_and_profile(client: TestClient) -> None:
    headers = _headers(client, "target@example.com")
    rest = client.get("/nutrition/day", headers=headers).json()["target"]
    assert rest["bmr"] == round(10 * 75 + 6.25 * 178 - 5 * (date.today().year - 1994) + 5)
    session = {
        "discipline": "boxing",
        "rawText": "boxeo",
        "durationMinutes": 60,
        "intensity": 8,
        "performedAt": datetime.now(UTC).isoformat(),
    }
    assert client.post("/sessions", json=session, headers=headers).status_code == 201
    trained = client.get("/nutrition/day", headers=headers).json()["target"]
    assert trained["trainingKcal"] > 0
    assert abs(trained["targetKcal"] - rest["targetKcal"] - trained["trainingKcal"]) <= 1

    incomplete = _headers(client, "no-profile@example.com", profile=False)
    day = client.get("/nutrition/day", headers=incomplete).json()
    assert day["target"] is None and "altura" in day["missingProfile"]


def test_goal_cut_and_weight_log(client: TestClient) -> None:
    headers = _headers(client, "cut@example.com")
    assert client.put("/nutrition/goal", json={"goal": "corte"}, headers=headers).status_code == 422
    target_date = (date.today() + timedelta(weeks=6)).isoformat()
    goal = {"goal": "corte", "targetWeightKg": 72, "targetDate": target_date}
    assert client.put("/nutrition/goal", json=goal, headers=headers).status_code == 200
    target = client.get("/nutrition/day", headers=headers).json()["target"]
    assert target["adjustmentKcal"] == -550 and target["rateKgWeek"] == -0.5

    for days_ago, kg in ((8, 75.6), (1, 74.8), (0, 74.6)):
        day = (date.today() - timedelta(days=days_ago)).isoformat()
        client.post("/nutrition/weight", json={"measuredOn": day, "weightKg": kg}, headers=headers)
    weight = client.get("/nutrition/weight", headers=headers).json()
    assert weight["latestKg"] == 74.6 and weight["changeWeekKg"] == round(74.7 - 75.6, 2)
    profile = client.get("/profile", headers=headers).json()
    assert profile["weightKg"] == 74.6


def test_weight_with_body_composition(client: TestClient) -> None:
    headers = _headers(client, "composition@example.com")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    body = {"measuredOn": yesterday, "weightKg": 80, "bodyFatPct": 18.5, "musclePct": 42}
    assert client.post("/nutrition/weight", json=body, headers=headers).status_code in (200, 201)
    # Hoy solo peso: la última composición sigue siendo la de ayer.
    client.post("/nutrition/weight", json={"measuredOn": TODAY, "weightKg": 79.6}, headers=headers)
    weight = client.get("/nutrition/weight", headers=headers).json()
    assert weight["latestKg"] == 79.6
    assert (weight["latestBodyFatPct"], weight["latestMusclePct"]) == (18.5, 42)
    assert weight["points"][0]["bodyFatPct"] == 18.5 and weight["points"][1]["bodyFatPct"] is None
    # Corregir el peso de ayer sin porcentajes no borra los medidos.
    client.post(
        "/nutrition/weight", json={"measuredOn": yesterday, "weightKg": 80.2}, headers=headers
    )
    again = client.get("/nutrition/weight", headers=headers).json()
    assert again["points"][0]["weightKg"] == 80.2 and again["points"][0]["bodyFatPct"] == 18.5
    bad = {"measuredOn": TODAY, "weightKg": 79, "bodyFatPct": 90}
    assert client.post("/nutrition/weight", json=bad, headers=headers).status_code == 422


def test_five_meals_and_snack_alias(client: TestClient) -> None:
    headers = _headers(client, "meals5@example.com")
    assert _entry(client, headers, name="Fruta", kcal=80, meal="snack").status_code == 201
    assert _entry(client, headers, name="Tostada", kcal=150, meal="media_manana").status_code == 201
    day = client.get("/nutrition/day", headers=headers).json()
    assert list(day["meals"])[:5] == ["desayuno", "media_manana", "comida", "merienda", "cena"]
    assert len(day["meals"]["media_manana"]) == 2 and "snack" not in day["meals"]


def test_templates(client: TestClient) -> None:
    headers = _headers(client, "templates@example.com")
    food = _food(client, headers)
    tpl = client.post(
        "/nutrition/templates",
        json={"name": "Desayuno habitual", "items": [{"foodId": food["id"], "grams": 20}]},
        headers=headers,
    ).json()
    assert tpl["kcal"] == 120
    applied = client.post(
        f"/nutrition/templates/{tpl['id']}/apply",
        json={"eatenOn": TODAY, "meal": "desayuno"},
        headers=headers,
    )
    assert applied.status_code == 201 and applied.json()[0]["kcal"] == 120


def test_barcode_uses_cache_after_first_lookup(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "barcode@example.com")
    nutella = FoodCandidate(
        source="off",
        external_id="3017620422003",
        barcode="3017620422003",
        name="Nutella",
        brand="Ferrero",
        kcal_100g=539,
        protein_100g=6.3,
        carbs_100g=57.5,
        fat_100g=30.9,
    )

    async def found(code: str) -> FoodCandidate:
        return nutella

    monkeypatch.setattr("app.core.food_sources.off_by_barcode", found)
    first = client.get("/nutrition/foods/barcode/3017620422003", headers=headers)
    assert first.status_code == 200 and first.json()["name"] == "Nutella"

    async def down(code: str) -> FoodCandidate:
        raise FoodSourceError("caído")

    monkeypatch.setattr("app.core.food_sources.off_by_barcode", down)
    cached = client.get("/nutrition/foods/barcode/3017620422003", headers=headers)
    assert cached.status_code == 200 and cached.json()["id"] == first.json()["id"]
    assert client.get("/nutrition/foods/barcode/1111111", headers=headers).status_code == 503
    assert client.get("/nutrition/foods/barcode/abc", headers=headers).status_code == 422


def test_search_prefers_own_foods(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _headers(client, "search@example.com")
    _food(client, headers)

    async def off(query: str, limit: int = 12) -> list[FoodCandidate]:
        return [
            FoodCandidate(
                source="off",
                external_id="1",
                name="Crema de cacahuete Y",
                kcal_100g=610,
                protein_100g=24,
                carbs_100g=14,
                fat_100g=50,
            )
        ]

    monkeypatch.setattr("app.core.food_sources.off_search", off)
    monkeypatch.setattr("app.services.nutrition.settings.off_remote_search", True)
    results = client.get("/nutrition/foods/search?q=cacahuete", headers=headers).json()
    assert results[0]["name"] == "Crema de cacahuete Marca X"
    assert any(r["name"] == "Crema de cacahuete Y" for r in results)


def test_search_matches_words_plurals_accents_and_brand(client: TestClient) -> None:
    headers = _headers(client, "search-words@example.com")
    for name, brand in [
        ("Copos de avena integral", "Crownfield"),
        ("Plátano de Canarias", None),
        ("Pan de molde", None),
    ]:
        body = {"name": name, "brand": brand, "kcal100g": 100}
        assert client.post("/nutrition/foods", json=body, headers=headers).status_code == 201

    def names(q: str) -> list[str]:
        found = client.get(f"/nutrition/foods/search?q={q}", headers=headers).json()
        return [r["name"] for r in found]

    assert names("avena integrales") == ["Copos de avena integral"]
    assert names("crownfield copos") == ["Copos de avena integral"]
    assert names("platanos") == ["Plátano de Canarias"]
    assert names("pan integral") == []


def test_search_filters_by_store_and_brand(client: TestClient, db_session_factory) -> None:
    import asyncio

    from app.models import Food

    async def seed() -> None:
        async with db_session_factory() as session:
            session.add_all(
                [
                    Food(
                        source="off",
                        external_id="a",
                        name="Yogur natural",
                        brand="Milbona",
                        store="Lidl",
                        kcal_100g=60,
                    ),
                    Food(
                        source="off",
                        external_id="b",
                        name="Queso fresco",
                        brand="Milbona",
                        store="Lidl",
                        kcal_100g=90,
                    ),
                    Food(
                        source="off",
                        external_id="c",
                        name="Yogur griego",
                        brand="Hacendado",
                        store="Mercadona",
                        kcal_100g=120,
                    ),
                    Food(
                        source="off", external_id="d", name="Only whey", brand="Big", kcal_100g=400
                    ),
                ]
            )
            await session.commit()

    asyncio.run(seed())
    headers = _headers(client, "filters@example.com")

    def names(params: str) -> list[str]:
        response = client.get(f"/nutrition/foods/search?{params}", headers=headers)
        assert response.status_code == 200, response.text
        return sorted(r["name"] for r in response.json())

    assert names("q=yogur") == ["Yogur griego", "Yogur natural"]
    assert names("q=yogur&store=lidl") == ["Yogur natural"]
    assert names("store=Lidl") == ["Queso fresco", "Yogur natural"]
    assert names("brand=big") == ["Only whey"]
    assert client.get("/nutrition/foods/search?q=y", headers=headers).status_code == 422

    facets = client.get("/nutrition/foods/facets", headers=headers).json()
    assert facets["stores"] == ["Lidl", "Mercadona"]
    assert facets["brands"] == ["Big", "Hacendado", "Milbona"]
    lidl = client.get("/nutrition/foods/facets?store=lidl", headers=headers).json()
    assert lidl["brands"] == ["Milbona"]


def test_search_terms() -> None:
    from app.services.nutrition import search_terms

    assert search_terms("Cereales integrales") == ["%cereal%", "%integr%"]
    assert search_terms("plátanos de Canarias") == ["%platan%", "%canari%"]


def test_free_text_proposal_and_batch(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _headers(client, "parse@example.com")
    _food(client, headers)

    async def parsed(text: str) -> dict[str, Any]:
        return {
            "source": "llm",
            "unresolved": ["tamaño de la tostada"],
            "items": [
                {"name": "pan de molde", "name_en": "bread, white", "grams": 60, "kcal_100g": 260},
                {
                    "name": "Crema de cacahuete Marca X",
                    "name_en": "peanut butter",
                    "grams": 32,
                    "kcal_100g": 590,
                },
                {"name": "salsa rara", "name_en": "", "grams": 20, "kcal_100g": 150},
            ],
        }

    async def usda(query: str, limit: int = 5) -> list[FoodCandidate]:
        return [
            FoodCandidate(
                source="usda",
                external_id="9",
                name="Bread, white",
                kcal_100g=266,
                protein_100g=7.6,
                carbs_100g=50.6,
                fat_100g=3.3,
            )
        ]

    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", parsed)
    monkeypatch.setattr("app.core.food_sources.usda_search", usda)
    proposal = client.post(
        "/nutrition/meals/parse", json={"text": "2 tostadas con crema"}, headers=headers
    ).json()
    sources = [i["source"] for i in proposal["items"]]
    assert sources == ["usda", "custom", "ia"]
    assert proposal["items"][0]["kcal100g"] == 266  # el dato real de USDA manda sobre la IA
    assert proposal["unresolved"] == ["tamaño de la tostada"]

    saved = client.post(
        "/nutrition/meals/batch",
        json={"eatenOn": TODAY, "meal": "merienda", "items": proposal["items"]},
        headers=headers,
    )
    assert saved.status_code == 201, saved.text
    assert [e["method"] for e in saved.json()] == ["ia", "ia", "ia"]
    day = client.get("/nutrition/day", headers=headers).json()
    assert day["estimatedKcal"] == round(266 * 0.6 + 600 * 0.32 + 150 * 0.2, 1)


def test_agent_logs_meal_with_confirmation(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-meal@example.com")

    async def parsed(text: str) -> dict[str, Any]:
        return {
            "source": "llm",
            "items": [
                {"name": "plátano", "name_en": "", "grams": 120, "kcal_100g": 89, "carbs_100g": 23}
            ],
        }

    monkeypatch.setattr("app.services.agent_tools.fetch_meal_parse", parsed)
    steps = [
        {
            "source": "llm",
            "action": "herramienta",
            "tool": "registrar_comida",
            "arguments": {"texto": "un plátano", "comida": "snack"},
        },
        {"source": "llm", "action": "responder", "message": "Confírmalo.", "arguments": {}},
    ]

    async def scripted(payload: dict[str, Any]) -> dict[str, Any]:
        return steps.pop(0)

    monkeypatch.setattr("app.core.agent.fetch_agent_step", scripted)
    reply = client.post(
        "/agent/message", json={"text": "me he comido un plátano"}, headers=headers
    ).json()
    action = reply["actions"][0]
    assert action["type"] == "save_meal" and "plátano" in action["summary"]
    assert client.get("/nutrition/day", headers=headers).json()["totals"]["kcal"] == 0
    assert client.post(f"/agent/actions/{action['id']}/confirm", headers=headers).status_code == 200
    day = client.get("/nutrition/day", headers=headers).json()
    assert day["meals"]["media_manana"][0]["kcal"] == round(89 * 1.2, 1)  # "snack" = media mañana


def test_usda_match_must_be_plausible() -> None:
    from app.services.nutrition import plausible_match

    powder = FoodCandidate(
        source="usda",
        external_id="1",
        name="Coffee, instant, with whitener",
        kcal_100g=549,
        protein_100g=5,
        carbs_100g=60,
        fat_100g=30,
    )
    milk_coffee = FoodCandidate(
        source="usda",
        external_id="2",
        name="Coffee, brewed, with milk",
        kcal_100g=38,
        protein_100g=2,
        carbs_100g=3,
        fat_100g=2,
    )
    assert plausible_match([powder], 45) is None  # mejor quedarse con la estimación
    assert plausible_match([powder, milk_coffee], 45) is milk_coffee
    assert plausible_match([], 45) is None and plausible_match([powder], None) is None
