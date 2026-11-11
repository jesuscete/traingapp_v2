import asyncio
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ExerciseCatalog


def _add_translated_exercise(factory: async_sessionmaker[AsyncSession]) -> uuid.UUID:
    async def run() -> uuid.UUID:
        async with factory() as db:
            exercise = ExerciseCatalog(
                name="Barbell Hip Thrust",
                normalized_name="barbell hip thrust",
                exercise_type="strength",
                muscle_map={"glutes": 1.0, "hamstrings": 0.4},
                details={"sourceId": "Barbell_Hip_Thrust", "nameEs": "Empuje de cadera con barra"},
            )
            db.add(exercise)
            await db.commit()
            return exercise.id

    return asyncio.run(run())


def _headers(client: TestClient) -> dict[str, str]:
    body = {"email": "es@example.com", "password": "password123", "name": "Es"}
    client.post("/auth/register", json=body)
    login = client.post("/auth/login", json={"email": body["email"], "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _session(name: str, exercise_id: uuid.UUID | None) -> dict[str, object]:
    exercise: dict[str, object] = {
        "name": name,
        "orderIndex": 0,
        "sets": [{"setNumber": 1, "entries": [{"entryOrder": 0, "reps": 8, "weight": 100}]}],
    }
    if exercise_id is not None:
        exercise["exerciseId"] = str(exercise_id)
    return {
        "rawText": "gym",
        "performedAt": "2026-09-01T18:00:00Z",
        "durationMinutes": 40,
        "exercises": [exercise],
    }


def test_exercise_id_and_spanish_name_resolve_catalog(
    client: TestClient, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    exercise_id = _add_translated_exercise(db_session_factory)
    headers = _headers(client)

    by_id = client.post(
        "/sessions/gym", json=_session("Mi hip thrust", exercise_id), headers=headers
    ).json()
    assert by_id["workoutExercises"][0]["exerciseId"] == str(exercise_id)

    by_spanish_name = client.post(
        "/sessions/gym", json=_session("Empuje de cadera con barra", None), headers=headers
    ).json()
    assert by_spanish_name["workoutExercises"][0]["exerciseId"] == str(exercise_id)
    impacts = {i["muscleGroup"]: i["activation"] for i in by_spanish_name["muscleImpacts"]}
    assert impacts.get("glutes") == 1.0
