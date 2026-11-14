"""Router determinista del chat: qué nodo atiende cada mensaje y que no se llama a la IA."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.chat.intent_router import classify, missing_equipment


@pytest.mark.parametrize(
    ("text", "intent", "weekday"),
    [
        ("Enséñame mi rutina", "routine", None),
        ("mi rutina", "routine", None),
        ("¿Qué me toca hoy?", "routine", 2),
        ("¿qué tengo mañana?", "routine", 3),
        ("¿Qué tengo el jueves?", "routine", 4),
        ("¿Cómo voy de fatiga?", "fatigue", None),
        ("¿Cuántas calorías llevo hoy?", "nutrition", None),
        ("No tengo balón medicinal", "alternatives", None),
        ("dame una alternativa al press banca", "alternatives", None),
        ("Quiero mejorar mi pegada en boxeo", "recommend", None),
        ("quiero crear una rutina", "guided", None),
        ("Empiezo el entrenamiento", "guided", None),
        ("He hecho el entreno de hoy", "guided", None),
        # Trampas del regex antiguo del frontend: no deben abrir el asistente de planes.
        ("¿Crees que mi rutina es muy dura?", "agent", None),
        ("Necesito cambiar un ejercicio de mi rutina", "agent", None),
        ("Sustituye el press banca por algo con mancuernas", "agent", None),
        ("¿Por qué tengo fatiga en el cuádriceps?", "agent", None),
        ("Registra: 6 rounds de saco y 20 min de comba", "agent", None),
        ("hola", "agent", None),
    ],
)
def test_classify(text: str, intent: str, weekday: int | None) -> None:
    route = classify(text, today=2)
    assert route.intent == intent, text
    if weekday is not None:
        assert route.weekday == weekday


def test_missing_equipment_words() -> None:
    assert missing_equipment("no tengo balon medicinal ni barra") == ["medicine ball", "barbell"]
    assert missing_equipment("sin mancuernas") == ["dumbbell"]
    assert missing_equipment("no tengo barra z") == ["e-z curl bar"]


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "Boxer"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _no_agent(payload: dict[str, Any]) -> dict[str, Any]:
    raise AssertionError("El agente (IA) no debería intervenir")


def _routine(client: TestClient, headers: dict[str, str], exercise_ids: list[str]) -> None:
    body = {
        "name": "Boxeo",
        "days": [
            {
                "dayOfWeek": 1,
                "dayType": "gimnasio",
                "label": "Potencia",
                "exercises": [
                    {
                        "exerciseId": exercise_id,
                        "orderIndex": index,
                        "sets": [{"setNumber": 1, "targetRepsMin": 4, "targetRepsMax": 6}],
                    }
                    for index, exercise_id in enumerate(exercise_ids)
                ],
            }
        ],
    }
    assert client.post("/routines", json=body, headers=headers).status_code == 201


@pytest.fixture
def ids(client: TestClient, seed_catalog) -> dict[str, str]:
    headers = _headers(client, "router-reader@example.com")
    return {
        e["normalizedName"]: e["id"]
        for e in client.get("/catalog/exercises", headers=headers).json()
    }


def test_routine_question_returns_card_without_ai(
    client: TestClient,
    ids: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    _block_real_llm: list[str],
) -> None:
    monkeypatch.setattr("app.core.agent.fetch_agent_step", _no_agent)
    headers = _headers(client, "router-routine@example.com")
    _routine(client, headers, [ids["press banca"]])
    data = client.post(
        "/agent/message", json={"text": "Enséñame mi rutina"}, headers=headers
    ).json()
    assert data["source"] == "rules"
    card = data["cards"][0]
    assert card["type"] == "routine" and card["title"] == "Boxeo"
    assert card["sections"][0]["items"][0]["title"] == "Press banca"
    assert "Boxeo" in data["reply"]
    assert _block_real_llm == []


def test_fatigue_and_nutrition_cards_without_ai(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.core.agent.fetch_agent_step", _no_agent)
    headers = _headers(client, "router-fatigue@example.com")
    fatigue = client.post("/agent/message", json={"text": "¿Cómo voy de fatiga?"}, headers=headers)
    assert fatigue.json()["cards"][0]["type"] == "fatigue"
    food = client.post("/agent/message", json={"text": "¿cuántas calorías llevo?"}, headers=headers)
    assert food.json()["cards"][0]["type"] == "nutrition"


def test_goal_then_missing_equipment_follow_up(
    client: TestClient, seed_catalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.core.agent.fetch_agent_step", _no_agent)
    headers = _headers(client, "router-pegada@example.com")
    client.put("/profile", json={"primarySport": "boxeo"}, headers=headers)
    rec = client.post(
        "/agent/message", json={"text": "Quiero mejorar mi pegada"}, headers=headers
    ).json()
    assert rec["source"] == "rules" and rec["cards"][0]["type"] == "exercises"
    names = [i["title"] for i in rec["cards"][0]["sections"][0]["items"]]
    assert "Lanzamiento de balón medicinal" in names

    alt = client.post(
        "/agent/message", json={"text": "No tengo balón medicinal"}, headers=headers
    ).json()
    assert alt["source"] == "rules", alt
    section = alt["cards"][0]["sections"][0]
    assert section["title"].startswith("En vez de Lanzamiento de balón medicinal")
    assert section["items"] and all(i["badge"] != "Balón medicinal" for i in section["items"])


def test_plan_request_hands_off_to_guided_flow(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.core.agent.fetch_agent_step", _no_agent)
    headers = _headers(client, "router-plan@example.com")
    data = client.post(
        "/agent/message", json={"text": "quiero crear una rutina"}, headers=headers
    ).json()
    assert data["handoff"] == "guided"


def test_disabled_node_falls_back_to_agent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "chat_rule_nodes", "guided")
    calls: list[dict[str, Any]] = []

    async def agent_step(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(payload)
        return {"source": "llm", "action": "responder", "message": "Vas bien.", "arguments": {}}

    monkeypatch.setattr("app.core.agent.fetch_agent_step", agent_step)
    headers = _headers(client, "router-off@example.com")
    data = client.post("/agent/message", json={"text": "¿Cómo voy de fatiga?"}, headers=headers)
    assert data.json()["source"] == "llm" and calls
