from fastapi.testclient import TestClient

from tests.test_auth import REGISTER, _register


def _auth_headers(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_doms_upsert_and_get(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    body = {
        "date": "2026-08-08",
        "entries": [
            {"muscleGroup": "shoulders", "pain": 7},
            {"muscleGroup": "triceps", "pain": 5},
            {"muscleGroup": "quadriceps", "pain": 2},
        ],
    }
    response = client.post("/stats/doms", headers=headers, json=body)
    assert response.status_code == 200
    saved = response.json()
    assert saved["date"] == "2026-08-08"
    pains = {e["muscleGroup"]: e["pain"] for e in saved["entries"]}
    assert pains == {"shoulders": 7, "triceps": 5, "quadriceps": 2}

    response = client.get("/stats/doms?day=2026-08-08", headers=headers)
    assert response.status_code == 200
    pains = {e["muscleGroup"]: e["pain"] for e in response.json()["entries"]}
    assert pains == {"shoulders": 7, "triceps": 5, "quadriceps": 2}


def test_doms_replaces_entries_and_clears_missing(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    client.post(
        "/stats/doms",
        headers=headers,
        json={
            "date": "2026-08-09",
            "entries": [{"muscleGroup": "back", "pain": 6}, {"muscleGroup": "core", "pain": 3}],
        },
    )
    response = client.post(
        "/stats/doms",
        headers=headers,
        json={
            "date": "2026-08-09",
            "entries": [{"muscleGroup": "back", "pain": 4}],
        },
    )
    assert response.status_code == 200
    pains = {e["muscleGroup"]: e["pain"] for e in response.json()["entries"]}
    assert pains == {"back": 4}


def test_doms_empty_day(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.get("/stats/doms?day=2026-08-08", headers=headers)
    assert response.status_code == 200
    assert response.json()["entries"] == []


def test_doms_requires_auth(client: TestClient) -> None:
    response = client.get("/stats/doms")
    assert response.status_code == 401
    response = client.post("/stats/doms", json={"date": "2026-08-08", "entries": []})
    assert response.status_code == 401


def test_readiness_accepts_hrv_and_resting_hr(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.post(
        "/stats/readiness",
        headers=headers,
        json={
            "date": "2026-08-08",
            "sleepHours": 7.5,
            "doms": 4,
            "restDay": False,
            "hrvScore": 0.72,
            "restingHr": 48.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hrvScore"] == 0.72
    assert body["restingHr"] == 48.0
