import uuid

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)
INTERNAL = {"X-Internal-Token": settings.internal_token}


def test_parse_endpoint(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: None)
    response = client.post(
        "/parse",
        json={
            "requestId": str(uuid.uuid4()),
            "rawText": "5x5 press banca 80kg",
        },
        headers=INTERNAL,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["discipline"] == "gym"
    assert data["exercises"][0]["weightKg"] == 80.0


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_endpoint_requires_internal_token() -> None:
    body = {"requestId": str(uuid.uuid4()), "rawText": "x"}
    assert client.post("/parse", json=body).status_code == 401
    wrong = {"X-Internal-Token": "nope"}
    review = {"routineName": "r", "payload": []}
    assert client.post("/analyze/routine", json=review, headers=wrong).status_code == 401
