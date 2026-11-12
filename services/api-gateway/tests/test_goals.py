from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.services import sport_registry


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "G"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_goals_crud_and_single_primary(client: TestClient) -> None:
    headers = _headers(client, "goals@example.com")
    race_day = (datetime.now(UTC) + timedelta(days=30)).date().isoformat()
    first = client.post(
        "/goals",
        json={
            "kind": "event",
            "title": "Triatlón olímpico",
            "sport": "triathlon",
            "targetDate": race_day,
        },
        headers=headers,
    )
    assert first.status_code == 201, first.text
    race = first.json()
    assert race["isPrimary"] and race["daysLeft"] == 30  # la primera es la principal

    fight = client.post(
        "/goals",
        json={"kind": "competition", "title": "Combate amateur", "isPrimary": True},
        headers=headers,
    ).json()
    goals = client.get("/goals", headers=headers).json()
    assert [g["isPrimary"] for g in goals] == [True, False]
    assert goals[0]["id"] == fight["id"]

    done = {**race, "done": True}
    assert client.put(f"/goals/{race['id']}", json=done, headers=headers).json()["done"]
    assert client.delete(f"/goals/{fight['id']}", headers=headers).status_code == 204
    other = _headers(client, "goals-other@example.com")
    assert client.delete(f"/goals/{race['id']}", headers=other).status_code == 404


def test_primary_sport_drives_analysis_and_home(client: TestClient) -> None:
    headers = _headers(client, "primary-sport@example.com")
    home = client.get("/stats/home", headers=headers).json()
    assert home["sport"] == "boxing" and home["primaryGoal"] is None

    client.put("/profile", json={"sports": ["boxeo"], "primarySport": "triatlon"}, headers=headers)
    assert client.get("/profile", headers=headers).json()["primarySport"] == "triatlon"
    assert client.get("/analysis/sport", headers=headers).json()["sport"] == "triathlon"
    client.post("/goals", json={"kind": "weight", "title": "Bajar a 75 kg"}, headers=headers)
    home = client.get("/stats/home", headers=headers).json()
    assert home["sportLabel"] == "Triatlón"
    assert home["primaryGoal"]["title"] == "Bajar a 75 kg"


def test_triathlon_profile_is_registered() -> None:
    doc = sport_registry.profile_doc("running")
    assert doc.sport == "triathlon"
    assert "triatlón" in sport_registry.compact_summary("triathlon").lower()
