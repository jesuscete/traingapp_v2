"""Comidas por texto con diccionario que aprende: la IA solo la primera vez."""

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.meal_dictionary import alias_key, split_phrases

TODAY = datetime.now(UTC).date().isoformat()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "dos tostadas con aceite y un café con leche",
            [("tostada con aceite", 2.0), ("cafe con leche", 1.0)],
        ),
        ("Hoy he desayunado 200 g de arroz, 2 huevos", [("arroz", 1.0), ("huevo", 2.0)]),
        ("apunta un plátano", [("platano", 1.0)]),
        ("medio aguacate + una cucharada de aceite", [("aguacate", 0.5), ("aceite", 1.0)]),
    ],
)
def test_split_phrases(text: str, expected: list[tuple[str, float]]) -> None:
    assert [(p.key, p.quantity) for p in split_phrases(text)] == expected


def test_alias_key_is_stable_for_plurals_and_accents() -> None:
    assert alias_key("Tostadas con Aceite") == alias_key("tostada con aceite")
    assert alias_key("el café con leche") == "cafe con leche"


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "Comidas"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class FakeMealAI:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, text: str) -> dict[str, Any]:
        self.calls.append(text)
        items: list[dict[str, Any]] = []
        for index, fragment in enumerate(text.split(" | ")):
            if "cafe" in fragment.lower() or "café" in fragment.lower():
                items.append(
                    {
                        "name": "café con leche",
                        "name_en": "",
                        "grams": 200,
                        "kcal_100g": 40,
                        "protein_100g": 2,
                        "phrase": index,
                    }
                )
            elif "tostada" in fragment.lower():
                count = 2 if fragment.lower().startswith("dos") else 1
                items += [
                    {
                        "name": "pan tostado",
                        "name_en": "",
                        "grams": 30 * count,
                        "kcal_100g": 260,
                        "phrase": index,
                    },
                    {
                        "name": "aceite de oliva",
                        "name_en": "",
                        "grams": 5 * count,
                        "kcal_100g": 884,
                        "phrase": index,
                    },
                ]
        return {"source": "llm", "items": items, "unresolved": []}


def test_second_time_comes_from_dictionary_without_ai(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai = FakeMealAI()
    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", ai)
    headers = _headers(client, "dict-1@example.com")
    first = client.post(
        "/nutrition/meals/parse",
        json={"text": "dos tostadas con aceite y un café con leche"},
        headers=headers,
    ).json()
    assert first["source"] == "llm" and len(ai.calls) == 1
    assert [i["name"] for i in first["items"]] == [
        "pan tostado",
        "aceite de oliva",
        "café con leche",
    ]

    # Otro usuario, otra cantidad: sale del diccionario compartido, sin IA.
    other = _headers(client, "dict-2@example.com")
    second = client.post(
        "/nutrition/meals/parse",
        json={"text": "una tostada con aceite, café con leche"},
        headers=other,
    ).json()
    assert second["source"] == "rules" and len(ai.calls) == 1
    grams = {i["name"]: i["grams"] for i in second["items"]}
    assert grams == {"pan tostado": 30, "aceite de oliva": 5, "café con leche": 200}
    assert all(i["source"] == "ia" for i in second["items"])  # se muestra como «estimado IA»


def test_only_unknown_fragments_go_to_ai(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai = FakeMealAI()
    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", ai)
    headers = _headers(client, "dict-3@example.com")
    client.post("/nutrition/meals/parse", json={"text": "café con leche"}, headers=headers)
    client.post(
        "/nutrition/meals/parse",
        json={"text": "café con leche y dos tostadas con aceite"},
        headers=headers,
    )
    assert ai.calls == ["café con leche", "dos tostadas con aceite"]


def test_saving_a_different_portion_is_remembered_for_you(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai = FakeMealAI()
    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", ai)
    headers = _headers(client, "dict-4@example.com")
    proposal = client.post(
        "/nutrition/meals/parse", json={"text": "café con leche"}, headers=headers
    ).json()
    item = {**proposal["items"][0], "grams": 300}  # mi café es grande
    saved = client.post(
        "/nutrition/meals/batch",
        json={"eatenOn": TODAY, "meal": "desayuno", "items": [item]},
        headers=headers,
    )
    assert saved.status_code == 201, saved.text
    again = client.post(
        "/nutrition/meals/parse", json={"text": "café con leche"}, headers=headers
    ).json()
    assert again["items"][0]["grams"] == 300 and len(ai.calls) == 1
    other = _headers(client, "dict-5@example.com")
    theirs = client.post(
        "/nutrition/meals/parse", json={"text": "café con leche"}, headers=other
    ).json()
    assert theirs["items"][0]["grams"] == 200  # la corrección es solo tuya


def test_without_ai_known_foods_still_work(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai = FakeMealAI()
    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", ai)
    headers = _headers(client, "dict-6@example.com")
    client.post("/nutrition/meals/parse", json={"text": "café con leche"}, headers=headers)

    async def down(text: str) -> dict[str, Any]:
        import httpx

        raise httpx.ConnectError("IA caída")

    monkeypatch.setattr("app.api.nutrition.fetch_meal_parse", down)
    result = client.post(
        "/nutrition/meals/parse",
        json={"text": "café con leche y un bocadillo raro"},
        headers=headers,
    ).json()
    assert [i["name"] for i in result["items"]] == ["café con leche"]
    assert result["unresolved"] == ["un bocadillo raro"]
