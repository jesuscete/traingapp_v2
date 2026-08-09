import json
import uuid

from fastapi.testclient import TestClient

REGISTER = {"email": "chat@example.com", "password": "password123", "name": "Chat"}

DRAFT_PAYLOAD = {
    "rawText": "5x5 press banca 80kg",
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


def _auth_headers(client: TestClient, email: str = REGISTER["email"]) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Chat"},
    )
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


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


def test_draft_returns_draft(client: TestClient, _fake_redis, monkeypatch) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client)

    response = client.post("/chat/draft", json={"text": "5x5 press banca 80kg"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["requestId"]
    assert data["draft"]["discipline"] == "gym"
    assert data["draft"]["suggestedRpe"] == 8.0
    assert data["draft"]["exercises"][0]["weightKg"] == 80


def test_confirm_creates_session(client: TestClient, _fake_redis, monkeypatch) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client)

    draft = client.post("/chat/draft", json={"text": "5x5 press banca 80kg"}, headers=headers)
    request_id = draft.json()["requestId"]

    response = client.post(
        "/chat/confirm",
        json={"requestId": request_id, "suggestedRpe": 9},
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["volumeKg"] == 2000
    assert created["details"]["rpe"] == 9

    repeat = client.post("/chat/confirm", json={"requestId": request_id}, headers=headers)
    assert repeat.status_code == 404


def test_confirm_persists_fatigue_and_returns_muscle_impacts(
    client: TestClient, _fake_redis, monkeypatch, seed_catalog
) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client, "impacts@example.com")

    draft = client.post("/chat/draft", json={"text": "5x5 press banca 80kg"}, headers=headers)
    request_id = draft.json()["requestId"]

    response = client.post(
        "/chat/confirm",
        json={"requestId": request_id, "suggestedRpe": 8, "perceivedFatigue": 6},
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["details"]["rpe"] == 8
    assert created["details"]["perceivedFatigue"] == 6

    impacts = created["muscleImpacts"]
    assert impacts[0]["muscleGroup"] == "chest"
    assert impacts[0]["activation"] == 1.0
    by_group = {item["muscleGroup"]: item["activation"] for item in impacts}
    assert by_group["triceps"] == 0.5
    assert by_group["shoulders"] == 0.167


def test_get_session_includes_muscle_impacts(
    client: TestClient, _fake_redis, monkeypatch, seed_catalog
) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client, "detail-impacts@example.com")

    draft = client.post("/chat/draft", json={"text": "5x5 press banca 80kg"}, headers=headers)
    request_id = draft.json()["requestId"]
    created = client.post("/chat/confirm", json={"requestId": request_id}, headers=headers)
    session_id = created.json()["id"]

    response = client.get(f"/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    impacts = response.json()["muscleImpacts"]
    assert impacts[0]["muscleGroup"] == "chest"
    assert impacts[0]["activation"] == 1.0


def test_confirm_with_edited_exercises(client: TestClient, _fake_redis, monkeypatch) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client, "edit@example.com")

    draft = client.post("/chat/draft", json={"text": "5x5 press banca 80kg"}, headers=headers)
    request_id = draft.json()["requestId"]

    response = client.post(
        "/chat/confirm",
        json={
            "requestId": request_id,
            "suggestedRpe": 7,
            "exercises": [
                {
                    "name": "press banca",
                    "sets": 4,
                    "reps": 7,
                    "perSetReps": [8, 7, 7, 5],
                    "weightKg": 80,
                }
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["volumeKg"] == 4 * 7 * 80
    assert created["details"]["rpe"] == 7


def test_confirm_cardio_with_distance_and_workout_type(
    client: TestClient, _fake_redis, monkeypatch
) -> None:
    async def _cardio_fetch(raw_text: str) -> dict:
        return {
            "rawText": raw_text,
            "discipline": "running",
            "performedAt": "2026-08-08T18:30:00Z",
            "durationMinutes": 45,
            "exercises": [],
            "suggestedRpe": 6.5,
            "confidence": 0.7,
            "unresolved": [],
        }

    monkeypatch.setattr("app.api.chat.fetch_draft", _cardio_fetch)
    headers = _auth_headers(client, "cardio@example.com")
    client.put("/profile", json={"weightKg": 75}, headers=headers)

    draft = client.post("/chat/draft", json={"text": "carrera de 45 min"}, headers=headers)
    request_id = draft.json()["requestId"]

    response = client.post(
        "/chat/confirm",
        json={
            "requestId": request_id,
            "suggestedRpe": 8,
            "perceivedFatigue": 4,
            "durationMinutes": 45,
            "distanceMeters": 9000,
            "workoutType": "interval",
        },
        headers=headers,
    )
    assert response.status_code == 201
    created = response.json()
    assert created["discipline"] == "running"
    assert created["distanceMeters"] == 9000
    assert created["estimatedKcal"] is not None
    assert created["estimatedKcal"] > 0
    assert created["details"]["rpe"] == 8
    assert created["details"]["workoutType"] == "interval"
    factors = " ".join(created["details"]["kcal_factors"])
    assert "9.0 km recorridos" in factors


def test_confirm_unknown_draft_404(client: TestClient, _fake_redis) -> None:
    headers = _auth_headers(client, "missing@example.com")
    response = client.post(
        "/chat/confirm",
        json={"requestId": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 404


def test_cancel_discards_draft(client: TestClient, _fake_redis, monkeypatch) -> None:
    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    headers = _auth_headers(client, "cancel@example.com")

    draft = client.post("/chat/draft", json={"text": "carrera de 30 min"}, headers=headers)
    request_id = draft.json()["requestId"]

    response = client.post("/chat/cancel", json={"requestId": request_id}, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    confirm = client.post("/chat/confirm", json={"requestId": request_id}, headers=headers)
    assert confirm.status_code == 404


def test_draft_requires_auth(client: TestClient) -> None:
    response = client.post("/chat/draft", json={"text": "carrera de 30 min"})
    assert response.status_code == 401
