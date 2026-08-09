import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_parse_endpoint() -> None:
    response = client.post(
        "/parse",
        json={
            "requestId": str(uuid.uuid4()),
            "rawText": "5x5 press banca 80kg",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["discipline"] == "gym"
    assert data["exercises"][0]["weightKg"] == 80.0


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
