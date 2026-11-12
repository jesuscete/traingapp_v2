"""M4.1: la fatiga sale de los ejercicios reales y se recupera de forma realista."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.analytics import fatigue as fatigue_analytics
from app.schemas.metrics import CombatBlock, CombatMetrics
from app.services.fatigue_input import combat_group_load, involvement, set_effort


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "F"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _gym(exercises: list[tuple[str, int]], days_ago: int = 0, rpe: int = 9) -> dict[str, Any]:
    return {
        "rawText": "gym",
        "performedAt": _iso(days_ago),
        "durationMinutes": 60,
        "exercises": [
            {
                "name": name,
                "orderIndex": i,
                "sets": [
                    {
                        "setNumber": n,
                        "entries": [{"entryOrder": 0, "reps": 8, "weight": 60, "rpe": rpe}],
                    }
                    for n in range(1, sets + 1)
                ],
            }
            for i, (name, sets) in enumerate(exercises)
        ],
    }


def _fatigue(client: TestClient, headers: dict[str, str]) -> dict[str, float]:
    muscles = client.get("/stats/fatigue", headers=headers).json()["muscles"]
    return {m["muscleGroup"]: m["fatigue"] for m in muscles}


def test_involvement_and_effort() -> None:
    assert involvement({"back": 0.75, "biceps": 0.25}) == {"back": 1.0, "biceps": 0.333}
    assert set_effort(10) == 1.0 and set_effort(8) == 0.88
    assert set_effort(None) == set_effort(8)
    assert set_effort(1) == 0.5  # mínimo


def test_leg_day_fatigues_legs_not_chest(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "legday@example.com")
    body = _gym([("sentadilla", 5), ("prensa", 4), ("peso muerto rumano", 4)])
    assert client.post("/sessions/gym", json=body, headers=headers).status_code == 201
    f = _fatigue(client, headers)
    assert f["quadriceps"] > 60
    assert f["chest"] == 0 and f["biceps"] == 0
    assert f["quadriceps"] > f["glutes"] > f["calves"]


def test_pullups_back_over_biceps_over_forearms(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "pullups@example.com")
    assert (
        client.post("/sessions/gym", json=_gym([("dominadas", 5)]), headers=headers).status_code
        == 201
    )
    f = _fatigue(client, headers)
    assert f["back"] > f["biceps"] > f["forearms"] > 0
    assert f["chest"] == 0 and f["quadriceps"] == 0


def test_recovery_is_prolonged_for_large_muscles(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "recovery@example.com")
    body = _gym([("sentadilla", 6), ("curl biceps", 6)], days_ago=3)
    assert client.post("/sessions/gym", json=body, headers=headers).status_code == 201
    f = _fatigue(client, headers)
    # A las 72 h queda fatiga residual en cuádriceps, y más que en bíceps.
    assert f["quadriceps"] > 10
    assert f["quadriceps"] > f["biceps"]


def test_projection_uses_compartments(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "projection@example.com")
    assert (
        client.post("/sessions/gym", json=_gym([("sentadilla", 6)]), headers=headers).status_code
        == 201
    )
    data = client.get("/stats/fatigue", headers=headers).json()
    today_max = data["maxFatigue"]
    tomorrow = data["projection"][0]["maxFatigue"]
    # Mañana se ha ido la parte aguda (~35 %) y parte de la residual.
    assert 0.45 * today_max < tomorrow < 0.65 * today_max


def test_combat_blocks_load_their_own_muscles() -> None:
    rope = combat_group_load(
        "boxing", CombatMetrics(blocks=[CombatBlock(type="comba", minutes=30)])
    )
    bag = combat_group_load(
        "boxing", CombatMetrics(blocks=[CombatBlock(type="saco", rounds=6, round_seconds=180)])
    )
    assert max(rope, key=lambda g: rope[g]) == "calves"
    assert max(bag, key=lambda g: bag[g]) == "shoulders"
    assert bag.get("calves", 0) < bag["shoulders"]


def test_saturation_replaces_hard_cap() -> None:
    big = fatigue_analytics.SessionData(discipline="running", distance_meters=30_000, rpe=8)
    huge = fatigue_analytics.SessionData(discipline="running", distance_meters=42_000, rpe=8)
    load_big = fatigue_analytics.session_load(big, fatigue_analytics.MUSCLE_LOAD_DEFAULT)
    load_huge = fatigue_analytics.session_load(huge, fatigue_analytics.MUSCLE_LOAD_DEFAULT)
    assert load_huge["quadriceps"] > load_big["quadriceps"]  # más volumen sigue sumando
