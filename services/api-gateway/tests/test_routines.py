import asyncio
import uuid
from typing import Any

from fastapi.testclient import TestClient

from app.models import Discipline


def _register(client: TestClient, email: str = "rut@example.com") -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Rut"},
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _exercise_id(client: TestClient, headers: dict[str, str], name: str) -> str:
    response = client.get("/catalog/exercises", headers=headers)
    assert response.status_code == 200
    for item in response.json():
        if item["normalizedName"] == name:
            return item["id"]
    raise AssertionError(f"Ejercicio {name!r} no encontrado en el catalogo")


def _gym_day(exercise_id: str, label: str = "Día de piernas") -> dict[str, Any]:
    return {
        "dayOfWeek": 1,
        "dayType": "gimnasio",
        "label": label,
        "exercises": [
            {
                "exerciseId": exercise_id,
                "orderIndex": 0,
                "sets": [
                    {"setNumber": 1, "setType": "normal", "targetRepsMin": 8, "targetRepsMax": 12},
                    {"setNumber": 2, "setType": "normal", "targetRepsMin": 8, "targetRepsMax": 12},
                ],
            }
        ],
    }


def _routine_payload(exercise_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "name": "Rutina A",
        "days": [_gym_day(exercise_id)],
    }
    payload.update(overrides)
    return payload


def _create_discipline(db_factory) -> uuid.UUID:
    async def run() -> uuid.UUID:
        async with db_factory() as session:
            discipline = Discipline(
                name="Running", normalized_name="running", met=8.2
            )
            session.add(discipline)
            await session.commit()
            return discipline.id

    return asyncio.run(run())


def test_create_routine_and_get_active(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client)
    exercise_id = _exercise_id(client, headers, "press banca")

    created = client.post(
        "/routines", json=_routine_payload(exercise_id), headers=headers
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Rutina A"
    assert body["isActive"] is True
    assert len(body["days"]) == 1
    day = body["days"][0]
    assert day["dayOfWeek"] == 1
    assert day["dayType"] == "gimnasio"
    assert day["label"] == "Día de piernas"
    exercise = day["exercises"][0]
    assert exercise["name"] == "Press banca"
    assert exercise["exerciseId"] == exercise_id
    assert len(exercise["sets"]) == 2

    active = client.get("/routines/active", headers=headers)
    assert active.status_code == 200
    assert active.json()["id"] == body["id"]


def test_only_one_active_routine(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "active@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")

    first = client.post(
        "/routines", json=_routine_payload(exercise_id), headers=headers
    )
    assert first.status_code == 201
    second = client.post(
        "/routines",
        json=_routine_payload(
            exercise_id,
            name="Rutina B",
            days=[_gym_day(exercise_id, "Día de empuje")],
        ),
        headers=headers,
    )
    assert second.status_code == 201
    assert second.json()["isActive"] is True

    active = client.get("/routines/active", headers=headers)
    assert active.json()["id"] == second.json()["id"]


def test_routine_day_validation(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "valid@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")

    deporte_sin_disciplina = {
        "name": "Rutina deporte",
        "days": [{"dayOfWeek": 2, "dayType": "deporte"}],
    }
    response = client.post(
        "/routines", json=deporte_sin_disciplina, headers=headers
    )
    assert response.status_code == 422

    gimnasio_sin_ejercicios = {
        "name": "Rutina gym",
        "days": [{"dayOfWeek": 3, "dayType": "gimnasio"}],
    }
    response = client.post(
        "/routines", json=gimnasio_sin_ejercicios, headers=headers
    )
    assert response.status_code == 422

    descanso_con_ejercicios = {
        "name": "Rutina descanso",
        "days": [
            {
                "dayOfWeek": 4,
                "dayType": "descanso",
                "exercises": [_gym_day(exercise_id)["exercises"][0]],
            }
        ],
    }
    response = client.post(
        "/routines", json=descanso_con_ejercicios, headers=headers
    )
    assert response.status_code == 422


def test_create_deporte_day_with_discipline(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "deporte@example.com")
    discipline_id = _create_discipline(db_session_factory)

    payload = {
        "name": "Rutina cardio",
        "days": [
            {
                "dayOfWeek": 5,
                "dayType": "deporte",
                "label": "Running",
                "disciplineId": str(discipline_id),
                "targetDurationMin": 40,
            }
        ],
    }
    created = client.post("/routines", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    day = created.json()["days"][0]
    assert day["dayType"] == "deporte"
    assert day["disciplineId"] == str(discipline_id)
    assert day["disciplineName"] == "Running"


def test_list_disciplines(client: TestClient, db_session_factory) -> None:
    _create_discipline(db_session_factory)
    headers = _register(client, "disc@example.com")
    response = client.get("/catalog/disciplines", headers=headers)
    assert response.status_code == 200
    names = {item["normalizedName"] for item in response.json()}
    assert "running" in names


def test_upsert_and_delete_day(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "upsert@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    created = client.post(
        "/routines", json=_routine_payload(exercise_id), headers=headers
    )
    routine_id = created.json()["id"]

    rest_day = {"dayType": "descanso", "label": "Descanso total"}
    upserted = client.put(
        f"/routines/{routine_id}/days/6", json=rest_day, headers=headers
    )
    assert upserted.status_code == 200, upserted.text
    days = {day["dayOfWeek"]: day for day in upserted.json()["days"]}
    assert days[6]["dayType"] == "descanso"
    assert days[6]["label"] == "Descanso total"

    deleted = client.delete(
        f"/routines/{routine_id}/days/6", headers=headers
    )
    assert deleted.status_code == 200
    assert all(day["dayOfWeek"] != 6 for day in deleted.json()["days"])


def test_routine_sets_allow_null_reps(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "nullreps@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")

    payload = _routine_payload(
        exercise_id,
        days=[
            {
                "dayOfWeek": 1,
                "dayType": "gimnasio",
                "label": "Día libre",
                "exercises": [
                    {
                        "exerciseId": exercise_id,
                        "orderIndex": 0,
                        "sets": [
                            {"setNumber": 1, "setType": "normal", "targetRepsMin": None},
                            {"setNumber": 2, "setType": "normal", "targetRepsMin": 10},
                        ],
                    }
                ],
            }
        ],
    )
    created = client.post("/routines", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    sets = created.json()["days"][0]["exercises"][0]["sets"]
    assert sets[0]["targetRepsMin"] is None
    assert sets[1]["targetRepsMin"] == 10


def test_delete_routine(
    client: TestClient, seed_catalog, db_session_factory
) -> None:
    headers = _register(client, "delete@example.com")
    exercise_id = _exercise_id(client, headers, "press banca")
    created = client.post(
        "/routines", json=_routine_payload(exercise_id), headers=headers
    )
    routine_id = created.json()["id"]

    deleted = client.delete(f"/routines/{routine_id}", headers=headers)
    assert deleted.status_code == 204

    active = client.get("/routines/active", headers=headers)
    assert active.json() is None
