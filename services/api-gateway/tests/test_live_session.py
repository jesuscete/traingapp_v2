import json

from fastapi.testclient import TestClient

from app.chat.conversation import is_end, is_start

DRAFT_PAYLOAD = {
    "rawText": "press banca 5x5 80kg; curl biceps 4x10 12kg",
    "discipline": "gym",
    "performedAt": "2026-08-08T18:30:00Z",
    "durationMinutes": 60,
    "exercises": [{"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80}],
    "suggestedRpe": 8.0,
    "confidence": 0.9,
    "unresolved": [],
}


async def _fake_fetch(raw_text: str) -> dict:
    return DRAFT_PAYLOAD


def _register(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Live"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_intent_detection() -> None:
    assert is_start("empiezo entrenamiento")
    assert is_start("Empiezo mi sesion de gimnasio")
    assert is_start("vamos a entrenar")
    assert not is_start("5x5 press banca 80kg")
    assert not is_start("he terminado")

    assert is_end("he terminado")
    assert is_end("termine el entrenamiento")
    assert is_end("HE ACABADO")
    assert not is_end("press banca 5x5 80kg")
    assert not is_end("empiezo entrenamiento")


def test_live_session_full_flow(
    client: TestClient, _fake_redis, monkeypatch
) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _register(client, "live@example.com")
    user_id = client.post(
        "/auth/login", json={"email": "live@example.com", "password": "password123"}
    ).json()["user"]["id"]

    started = client.post(
        "/chat/draft", json={"text": "empiezo entrenamiento"}, headers=headers
    )
    assert started.status_code == 200
    start_data = started.json()
    assert start_data["mode"] == "live"
    assert start_data["liveSessionId"]
    assert start_data["entriesCount"] == 0
    assert start_data["requestId"] is None

    appended = client.post(
        "/chat/draft", json={"text": "press banca 5x5 80kg"}, headers=headers
    )
    assert appended.json()["mode"] == "live"
    assert appended.json()["entriesCount"] == 1

    appended = client.post(
        "/chat/draft", json={"text": "curl biceps 4x10 12kg"}, headers=headers
    )
    assert appended.json()["mode"] == "live"
    assert appended.json()["entriesCount"] == 2

    closed = client.post("/chat/draft", json={"text": "he terminado"}, headers=headers)
    assert closed.status_code == 200
    end_data = closed.json()
    assert end_data["mode"] == "confirm"
    assert end_data["requestId"]
    assert end_data["liveSessionId"] == start_data["liveSessionId"]
    assert end_data["startedAt"] == start_data["startedAt"]
    assert end_data["entriesCount"] == 2
    assert end_data["draft"]["performedAt"] == start_data["startedAt"]

    confirmed = client.post(
        "/chat/confirm", json={"requestId": end_data["requestId"]}, headers=headers
    )
    assert confirmed.status_code == 201
    assert confirmed.json()["volumeKg"] == 2000

    assert f"live:session:{user_id}" not in _fake_redis.lists


def test_live_end_without_session_falls_back_to_direct(
    client: TestClient, _fake_redis, monkeypatch
) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _register(client, "endless@example.com")

    response = client.post("/chat/draft", json={"text": "he terminado"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["mode"] == "direct"
    assert response.json()["requestId"]


def test_append_without_live_is_direct(
    client: TestClient, _fake_redis, monkeypatch
) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _register(client, "appendless@example.com")

    response = client.post(
        "/chat/draft", json={"text": "press banca 5x5 80kg"}, headers=headers
    )
    assert response.json()["mode"] == "direct"
    assert response.json()["requestId"]


def test_live_session_ttl_persisted(client: TestClient, _fake_redis) -> None:
    headers = _register(client, "ttl@example.com")
    user_id = client.post(
        "/auth/login", json={"email": "ttl@example.com", "password": "password123"}
    ).json()["user"]["id"]

    client.post("/chat/draft", json={"text": "empiezo entrenamiento"}, headers=headers)

    stored = json.loads(_fake_redis.lists[f"live:session:{user_id}"][0])
    assert stored["liveSessionId"]
    assert stored["entries"] == []
    assert stored["startedAt"]
