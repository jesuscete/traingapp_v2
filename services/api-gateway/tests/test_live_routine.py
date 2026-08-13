from datetime import UTC, datetime

from fastapi.testclient import TestClient

from tests.test_routines import (
    _exercise_id,
    _gym_day,
    _register,
    _routine_payload,
)


def _create_routine(
    client: TestClient,
    headers: dict[str, str],
    exercise_id: str,
    label: str = "Día de piernas",
) -> dict:
    response = client.post(
        "/routines",
        json=_routine_payload(exercise_id, days=[_gym_day(exercise_id, label)]),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _seed_history(client: TestClient, headers: dict[str, str], exercise_id: str) -> None:
    payload = {
        "rawText": "press banca 2x80kg",
        "performedAt": datetime.now(UTC).isoformat(),
        "durationMinutes": 30,
        "exercises": [
            {
                "exerciseId": exercise_id,
                "name": "Press banca",
                "orderIndex": 0,
                "sets": [
                    {
                        "setNumber": 1,
                        "setType": "normal",
                        "entries": [{"entryOrder": 0, "reps": 8, "weight": 80.0}],
                    },
                    {
                        "setNumber": 2,
                        "setType": "normal",
                        "entries": [{"entryOrder": 0, "reps": 8, "weight": 82.5}],
                    },
                ],
            }
        ],
    }
    response = client.post("/sessions/gym", json=payload, headers=headers)
    assert response.status_code == 201, response.text


def test_live_start_prepopulates_from_routine(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "prepop@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    routine = _create_routine(client, headers, exercise_id)
    day_id = routine["days"][0]["id"]

    started = client.post("/live/start", json={"routineDayId": day_id}, headers=headers)
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["origin"] == "routine"
    assert body["discipline"] == "gym"
    assert body["routineDayId"] == day_id
    assert len(body["exercises"]) == 1
    exercise = body["exercises"][0]
    assert exercise["name"] == "Press banca"
    assert exercise["exerciseId"] == exercise_id
    assert len(exercise["sets"]) == 2
    assert all(item["weight"] is None for item in exercise["sets"])
    assert all(item["suggestedWeight"] is None for item in exercise["sets"])
    assert [item["setNumber"] for item in exercise["sets"]] == [1, 2]
    assert [item["targetRepsMin"] for item in exercise["sets"]] == [8, 8]


def test_live_start_suggests_weight_from_history(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "suggest@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    _seed_history(client, headers, exercise_id)
    routine = _create_routine(client, headers, exercise_id)
    day_id = routine["days"][0]["id"]

    started = client.post("/live/start", json={"routineDayId": day_id}, headers=headers)
    assert started.status_code == 200
    sets = started.json()["exercises"][0]["sets"]
    assert sets[0]["suggestedWeight"] == 80.0
    assert sets[1]["suggestedWeight"] == 82.5


def test_live_finish_discards_sets_without_weight(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "discard@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    routine = _create_routine(client, headers, exercise_id)
    day_id = routine["days"][0]["id"]
    client.post("/live/start", json={"routineDayId": day_id}, headers=headers)

    # Solo se rellena la serie 1: la 2 (sin peso) debe descartarse al finalizar.
    updated = client.patch(
        "/live/set",
        json={"exerciseIndex": 0, "setNumber": 1, "weight": 80.0, "reps": 10},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["exercises"][0]["sets"][0]["weight"] == 80.0

    finished = client.post(
        "/live/finish", json={"durationMinutes": 40}, headers=headers
    )
    assert finished.status_code == 201, finished.text
    session = finished.json()
    assert session["discipline"] == "gym"
    assert len(session["workoutExercises"]) == 1
    sets = session["workoutExercises"][0]["sets"]
    assert len(sets) == 1
    assert sets[0]["setNumber"] == 1
    assert sets[0]["entries"][0]["weight"] == 80.0
    assert sets[0]["entries"][0]["reps"] == 10

    # La sesion en vivo queda cerrada.
    live = client.get("/live", headers=headers)
    assert live.json() is None


def test_live_finish_without_weight_returns_400(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "nopeso@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    routine = _create_routine(client, headers, exercise_id)
    day_id = routine["days"][0]["id"]
    client.post("/live/start", json={"routineDayId": day_id}, headers=headers)

    finished = client.post(
        "/live/finish", json={"durationMinutes": 40}, headers=headers
    )
    assert finished.status_code == 400


def test_live_cancel_clears_session(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "cancel@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    routine = _create_routine(client, headers, exercise_id)
    day_id = routine["days"][0]["id"]
    client.post("/live/start", json={"routineDayId": day_id}, headers=headers)

    cancelled = client.delete("/live", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    live = client.get("/live", headers=headers)
    assert live.json() is None


def test_chat_routine_start_by_label(
    client: TestClient, seed_catalog, _fake_redis
) -> None:
    headers = _register(client, "chatrut@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    _create_routine(client, headers, exercise_id, label="Día de piernas")

    started = client.post(
        "/chat/draft", json={"text": "he hecho el dia de piernas"}, headers=headers
    )
    assert started.status_code == 200, started.text
    body = started.json()
    assert body["mode"] == "routine"
    assert body["liveSessionId"]

    live = client.get("/live", headers=headers)
    assert live.status_code == 200
    assert live.json()["origin"] == "routine"
    assert live.json()["discipline"] == "gym"


def test_chat_routine_start_falls_back_without_routine(
    client: TestClient, seed_catalog, _fake_redis, monkeypatch
) -> None:
    headers = _register(client, "norut@example.com")

    async def _fake_fetch(raw_text: str) -> dict:
        return {
            "rawText": raw_text,
            "discipline": "gym",
            "performedAt": "2026-08-08T18:30:00Z",
            "durationMinutes": 60,
            "exercises": [{"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80}],
            "suggestedRpe": 8.0,
            "confidence": 0.9,
            "unresolved": [],
        }

    monkeypatch.setattr("app.api.chat.fetch_draft", _fake_fetch)
    response = client.post(
        "/chat/draft", json={"text": "he hecho el dia de piernas"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["mode"] == "direct"
