import json

from fastapi.testclient import TestClient

REGISTER = {"email": "chat@example.com", "password": "password123", "name": "Chat"}


def test_enqueue_message(client: TestClient, _fake_redis) -> None:
    response = client.post("/auth/register", json=REGISTER)
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    response = client.post(
        "/chat/message", json={"text": "5x5 press banca 80kg"}, headers=headers
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["requestId"]

    items = _fake_redis.lists["workout:parse"]
    assert len(items) == 1
    payload = json.loads(items[0])
    assert payload["requestId"] == data["requestId"]
    assert payload["rawText"] == "5x5 press banca 80kg"


def test_enqueue_requires_auth(client: TestClient) -> None:
    response = client.post("/chat/message", json={"text": "carrera de 30 min"})
    assert response.status_code == 401


def test_internal_create_session_requires_token(client: TestClient) -> None:
    body = {
        "userId": "550e8400-e29b-41d4-a716-446655440000",
        "session": {
            "discipline": "boxing",
            "rawText": "clase de boxeo de 1h30m",
            "performedAt": "2026-08-08T19:00:00Z",
            "durationMinutes": 90,
            "exercises": [],
        },
    }
    response = client.post("/internal/sessions", json=body)
    assert response.status_code == 401


def test_internal_create_session(client: TestClient) -> None:
    register = client.post(
        "/auth/register",
        json={"email": "int@example.com", "password": "password123", "name": "Int"},
    )
    user_id = register.json()["user"]["id"]

    body = {
        "userId": user_id,
        "session": {
            "discipline": "gym",
            "rawText": "5x5 press banca 80kg",
            "performedAt": "2026-08-08T18:30:00Z",
            "durationMinutes": 60,
            "exercises": [{"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80}],
        },
    }
    headers = {"X-Internal-Token": "internal-dev-token"}
    response = client.post("/internal/sessions", json=body, headers=headers)
    assert response.status_code == 201
    assert response.json()["volumeKg"] == 2000
