"""Aislamiento entre usuarios: B no ve ni modifica recursos de A (404, sin revelar existencia)."""

from typing import Any

from fastapi.testclient import TestClient

SESSION = {
    "discipline": "boxing",
    "rawText": "boxeo 1h",
    "performedAt": "2026-08-09T19:00:00Z",
    "durationMinutes": 60,
    "exercises": [],
}

GYM_SESSION = {
    "rawText": "entreno gym",
    "performedAt": "2026-08-09T18:30:00Z",
    "durationMinutes": 60,
    "exercises": [
        {
            "name": "press banca",
            "orderIndex": 0,
            "sets": [
                {
                    "setNumber": 1,
                    "setType": "normal",
                    "isWarmup": False,
                    "entries": [
                        {
                            "entryOrder": 0,
                            "reps": 5,
                            "weight": 80,
                            "weightUnit": "kg",
                            "side": "both",
                        }
                    ],
                }
            ],
        }
    ],
}

REST_DAY: dict[str, Any] = {"dayType": "descanso", "label": "Descanso"}


def _headers(client: TestClient, email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": "password123", "name": "U"})
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create(client: TestClient, path: str, body: dict[str, Any], headers: dict[str, str]) -> str:
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_sessions_isolated_between_users(client: TestClient) -> None:
    owner = _headers(client, "owner-s@example.com")
    intruder = _headers(client, "intruder-s@example.com")
    session_id = _create(client, "/sessions", SESSION, owner)

    assert client.get(f"/sessions/{session_id}", headers=intruder).status_code == 404
    assert client.delete(f"/sessions/{session_id}", headers=intruder).status_code == 404
    assert session_id not in {
        s["id"] for s in client.get("/sessions", headers=intruder).json()["items"]
    }
    assert client.get(f"/sessions/{session_id}", headers=owner).status_code == 200


def test_gym_sessions_isolated_between_users(client: TestClient) -> None:
    owner = _headers(client, "owner-g@example.com")
    intruder = _headers(client, "intruder-g@example.com")
    gym_id = _create(client, "/sessions/gym", GYM_SESSION, owner)

    assert client.get(f"/sessions/gym/{gym_id}", headers=intruder).status_code == 404
    assert client.get(f"/sessions/{gym_id}", headers=intruder).status_code == 404
    assert client.delete(f"/sessions/{gym_id}", headers=intruder).status_code == 404
    assert gym_id not in {s["id"] for s in client.get("/sessions/gym", headers=intruder).json()}
    assert client.get(f"/sessions/gym/{gym_id}", headers=owner).status_code == 200


def test_routines_isolated_between_users(client: TestClient) -> None:
    owner = _headers(client, "owner-r@example.com")
    intruder = _headers(client, "intruder-r@example.com")
    routine_id = _create(
        client, "/routines", {"name": "Rutina A", "days": [{"dayOfWeek": 1, **REST_DAY}]}, owner
    )

    assert (
        client.put(f"/routines/{routine_id}", json={"name": "Hack"}, headers=intruder).status_code
        == 404
    )
    assert (
        client.put(f"/routines/{routine_id}/days/2", json=REST_DAY, headers=intruder).status_code
        == 404
    )
    assert client.delete(f"/routines/{routine_id}/days/1", headers=intruder).status_code == 404
    assert client.delete(f"/routines/{routine_id}", headers=intruder).status_code == 404
    assert client.get("/routines", headers=intruder).json() == []
    active = client.get("/routines/active", headers=intruder)
    assert active.status_code in (200, 404)
    assert active.status_code == 404 or active.json() is None

    owned = client.get("/routines", headers=owner).json()
    assert [(r["id"], r["name"], len(r["days"])) for r in owned] == [(routine_id, "Rutina A", 1)]
