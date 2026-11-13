from datetime import UTC, datetime
from typing import Any

from fastapi.testclient import TestClient

from app.analytics.catalog import normalize_exercise_name
from app.analytics.catalog_seed import MUSCLE_ROLLUP
from app.analytics.discipline_seed import DISCIPLINE_SEED
from app.analytics.fatigue import MUSCLE_LOAD_DEFAULT, SATURATION_K, WOD_REF_MINUTES
from app.analytics.wod_exercise_seed import WOD_EXERCISE_SEED
from app.models import TrainingSession
from app.schemas.metrics import WodMetrics
from app.services.fatigue_input import MuscleMaps, session_data


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "W"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _session(discipline: str, **extra: Any) -> dict[str, Any]:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    return {"discipline": discipline, "rawText": f"{discipline} test", "performedAt": now, **extra}


CINDY = {
    "kind": "wod",
    "format": "amrap",
    "name": "Cindy",
    "timeCapMinutes": 20,
    "rounds": 18,
    "extraReps": 7,
    "rx": True,
    "movements": [
        {"name": "Dominadas", "reps": 5},
        {"name": "Flexiones", "reps": 10},
        {"name": "Sentadilla con peso corporal", "reps": 15},
    ],
}


def test_crossfit_amrap_is_stored_and_duration_comes_from_time_cap(client: TestClient) -> None:
    headers = _headers(client, "wod@example.com")
    response = client.post(
        "/sessions", json=_session("crossfit", metrics=CINDY, intensity=8), headers=headers
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["durationMinutes"] == 20
    stored = data["details"]["metrics"]
    assert (stored["format"], stored["rounds"], stored["extraReps"]) == ("amrap", 18, 7)
    assert stored["movements"][0] == {"name": "Dominadas", "reps": 5}


def test_hyrox_splits_fill_duration(client: TestClient) -> None:
    headers = _headers(client, "hyrox@example.com")
    metrics = {
        "kind": "wod",
        "format": "hyrox_sim",
        "hyroxCategory": "open_men",
        "splits": [{"name": "Run 1", "seconds": 290}, {"name": "SkiErg", "seconds": 255}],
        "movements": [{"name": "SkiErg", "distanceM": 1000}],
    }
    response = client.post("/sessions", json=_session("hyrox", metrics=metrics), headers=headers)
    assert response.status_code == 201, response.text
    assert response.json()["durationMinutes"] == 10  # 545 s -> 10 min


def test_wod_metrics_rejected_for_other_disciplines(client: TestClient) -> None:
    headers = _headers(client, "wod-boxing@example.com")
    response = client.post("/sessions", json=_session("boxing", metrics=CINDY), headers=headers)
    assert response.status_code == 422


def test_score_text() -> None:
    assert WodMetrics(time_seconds=185).score_text() == "3:05"
    assert WodMetrics(rounds=18, extra_reps=7).score_text() == "18 rondas + 7"
    assert WodMetrics(load_kg=102.5).score_text() == "102.5 kg"


def test_seed_is_consistent() -> None:
    names = [normalize_exercise_name(e["name"]) for e in WOD_EXERCISE_SEED]
    assert len(names) == len(set(names))
    for entry in WOD_EXERCISE_SEED:
        assert sum(entry["muscles"].values()) <= 1.0001, entry["name"]
        assert set(entry["muscles"]) <= set(MUSCLE_ROLLUP), entry["name"]
    seeded = {d[1] for d in DISCIPLINE_SEED}
    assert {"crossfit", "hyrox"} <= seeded and {"crossfit", "hyrox"} <= set(MUSCLE_LOAD_DEFAULT)


def _wod_session(metrics: dict[str, Any], minutes: int | None = 20) -> TrainingSession:
    return TrainingSession(
        discipline="crossfit",
        raw_text="wod",
        duration_minutes=minutes,
        intensity=8,
        details={"metrics": metrics},
    )


def test_wod_fatigue_follows_movements() -> None:
    maps = MuscleMaps(
        by_id={},
        by_name={
            "thruster con barra": {"quadriceps": 0.35, "shoulders": 0.25, "glutes": 0.15},
            "pullups": {"back": 0.75, "biceps": 0.25},
        },
    )
    fran = {
        "kind": "wod",
        "format": "for_time",
        "timeSeconds": 300,
        "movements": [{"name": "Thruster con barra", "reps": 45}, {"name": "Pullups", "reps": 45}],
    }
    data = session_data(_wod_session(fran, minutes=None), maps)
    load = data.group_load or {}
    # 5 min de trabajo: cuádriceps (principal del thruster) y espalda (de la dominada) por igual.
    assert load["quadriceps"] == load["back"] == round(SATURATION_K * 5 / WOD_REF_MINUTES / 2, 4)
    assert load["shoulders"] < load["quadriceps"] and "chest" not in load


def test_wod_without_known_movements_uses_discipline_default() -> None:
    data = session_data(_wod_session({"kind": "wod", "format": "amrap"}), None)
    assert data.group_load is None
