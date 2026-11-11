from typing import Any

from fastapi.testclient import TestClient

CUSTOM = {
    "name": "Press landmine arrodillado",
    "primaryMuscles": ["shoulders"],
    "secondaryMuscles": ["chest", "triceps"],
    "equipment": "barra",
}


def _headers(client: TestClient, email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": "password123", "name": "C"})
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _visible_names(client: TestClient, headers: dict[str, str]) -> set[str]:
    return {e["name"] for e in client.get("/catalog/exercises", headers=headers).json()}


def _gym(exercise_id: str) -> dict[str, Any]:
    return {
        "rawText": "gym",
        "performedAt": "2026-09-03T18:00:00Z",
        "durationMinutes": 30,
        "exercises": [
            {
                "exerciseId": exercise_id,
                "name": CUSTOM["name"],
                "orderIndex": 0,
                "sets": [
                    {"setNumber": 1, "entries": [{"entryOrder": 0, "reps": 10, "weight": 30}]}
                ],
            }
        ],
    }


def test_custom_exercise_lifecycle_and_isolation(client: TestClient, seed_catalog) -> None:
    owner = _headers(client, "custom-owner@example.com")
    other = _headers(client, "custom-other@example.com")

    created = client.post("/catalog/exercises", json=CUSTOM, headers=owner)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["isCustom"] is True
    assert body["muscleMap"] == {"shoulders": 1.0, "chest": 0.5, "triceps": 0.5}
    exercise_id = body["id"]

    assert CUSTOM["name"] in _visible_names(client, owner)
    assert CUSTOM["name"] not in _visible_names(client, other)
    assert client.post("/catalog/exercises", json=CUSTOM, headers=owner).status_code == 409
    assert client.post("/catalog/exercises", json=CUSTOM, headers=other).status_code == 201

    session = client.post("/sessions/gym", json=_gym(exercise_id), headers=owner).json()
    assert session["workoutExercises"][0]["exerciseId"] == exercise_id
    history = client.get(f"/catalog/exercises/{exercise_id}/history", headers=owner).json()
    assert history["records"]["maxWeightKg"] == 30

    foreign = f"/catalog/exercises/{exercise_id}"
    assert client.get(f"{foreign}/history", headers=other).status_code == 404
    assert client.put(f"{foreign}/favorite", headers=other).status_code == 404
    assert client.delete(foreign, headers=other).status_code == 404

    assert client.delete(foreign, headers=owner).status_code == 204
    assert CUSTOM["name"] not in _visible_names(client, owner)


def test_custom_name_cannot_shadow_global(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "custom-shadow@example.com")
    body = {**CUSTOM, "name": "Press Banca"}
    assert client.post("/catalog/exercises", json=body, headers=headers).status_code == 409


def test_cannot_delete_global_exercise(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "custom-global@example.com")
    press = next(
        e
        for e in client.get("/catalog/exercises", headers=headers).json()
        if e["normalizedName"] == "press banca"
    )
    assert client.delete(f"/catalog/exercises/{press['id']}", headers=headers).status_code == 404


def test_custom_exercise_in_routine_cannot_be_deleted(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "custom-routine@example.com")
    exercise_id = client.post("/catalog/exercises", json=CUSTOM, headers=headers).json()["id"]
    routine = {
        "name": "Rutina C",
        "days": [
            {
                "dayOfWeek": 1,
                "dayType": "gimnasio",
                "exercises": [
                    {
                        "exerciseId": exercise_id,
                        "orderIndex": 0,
                        "sets": [{"setNumber": 1, "setType": "normal"}],
                    }
                ],
            }
        ],
    }
    assert client.post("/routines", json=routine, headers=headers).status_code == 201
    assert client.delete(f"/catalog/exercises/{exercise_id}", headers=headers).status_code == 409


def test_routine_rejects_foreign_or_unknown_exercises(client: TestClient, seed_catalog) -> None:
    owner = _headers(client, "routine-owner@example.com")
    other = _headers(client, "routine-other@example.com")
    foreign_id = client.post("/catalog/exercises", json=CUSTOM, headers=owner).json()["id"]

    def routine(exercise_id: str) -> dict[str, Any]:
        return {
            "name": "R",
            "days": [
                {
                    "dayOfWeek": 1,
                    "dayType": "gimnasio",
                    "exercises": [
                        {
                            "exerciseId": exercise_id,
                            "orderIndex": 0,
                            "sets": [{"setNumber": 1, "setType": "normal"}],
                        }
                    ],
                }
            ],
        }

    assert client.post("/routines", json=routine(foreign_id), headers=other).status_code == 422
    unknown = "00000000-0000-0000-0000-000000000000"
    assert client.post("/routines", json=routine(unknown), headers=other).status_code == 422
