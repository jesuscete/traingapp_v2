from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

REGISTER = {"email": "stats@example.com", "password": "password123", "name": "Stats"}


def _headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/register", json=REGISTER)
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _iso(days_ago: int) -> str:
    moment = datetime.now(UTC) - timedelta(days=days_ago)
    return moment.isoformat().replace("+00:00", "Z")


def _create_gym(
    client: TestClient,
    headers: dict[str, str],
    *,
    days_ago: int,
    name: str,
    sets: int = 5,
    reps: int = 5,
    weight_kg: int = 80,
) -> None:
    payload = {
        "discipline": "gym",
        "rawText": f"{sets}x{reps} {name} {weight_kg}kg",
        "performedAt": _iso(days_ago),
        "durationMinutes": 60,
        "exercises": [{"name": name, "sets": sets, "reps": reps, "weightKg": weight_kg}],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 201


def _create_cardio(
    client: TestClient,
    headers: dict[str, str],
    *,
    discipline: str,
    days_ago: int,
    duration_minutes: int,
) -> None:
    payload = {
        "discipline": discipline,
        "rawText": f"{discipline} session",
        "performedAt": _iso(days_ago),
        "durationMinutes": duration_minutes,
        "exercises": [],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 201


def test_stats_require_auth(client: TestClient) -> None:
    for path in ("/stats/overview", "/stats/volume", "/stats/cardio", "/stats/progress"):
        assert client.get(path).status_code == 401


def test_overview_aggregates(client: TestClient) -> None:
    headers = _headers(client)
    _create_gym(client, headers, days_ago=3, name="press banca")
    _create_gym(client, headers, days_ago=8, name="sentadilla")
    _create_cardio(client, headers, discipline="boxing", days_ago=10, duration_minutes=90)

    response = client.get("/stats/overview", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["periodDays"] == 30
    assert data["totalSessions"] == 3
    assert data["totalVolumeKg"] == 4000
    assert data["totalDurationMinutes"] == 210
    assert len(data["byDiscipline"]) == 2
    assert len(data["weeklyVolume"]) >= 1
    gym = next(item for item in data["byDiscipline"] if item["discipline"] == "gym")
    assert gym["sessions"] == 2


def test_volume_by_muscle_group(client: TestClient) -> None:
    headers = _headers(client)
    _create_gym(client, headers, days_ago=2, name="press banca", weight_kg=80)
    _create_gym(client, headers, days_ago=4, name="sentadilla", weight_kg=100)

    response = client.get("/stats/volume", headers=headers)
    assert response.status_code == 200
    data = response.json()
    groups = {item["muscleGroup"]: item for item in data["byMuscleGroup"]}
    assert groups["chest"]["volumeKg"] == 2000
    assert groups["legs"]["volumeKg"] == 2500
    assert data["unclassifiedVolumeKg"] == 0

    press = next(item for item in data["exerciseProgress"] if item["exercise"] == "press banca")
    assert press["best1Rm"] == 80 * (1 + 5 / 30)
    assert press["sessions"] == 1
    assert press["deltaPct"] == 0


def test_volume_unknown_exercise_is_unclassified(client: TestClient) -> None:
    headers = _headers(client)
    _create_gym(client, headers, days_ago=2, name="movimiento random", weight_kg=50)

    response = client.get("/stats/volume", headers=headers)
    data = response.json()
    assert data["unclassifiedVolumeKg"] == 1250
    assert data["byMuscleGroup"] == []


def test_cardio_aggregates_duration(client: TestClient) -> None:
    headers = _headers(client)
    _create_cardio(client, headers, discipline="running", days_ago=1, duration_minutes=45)
    _create_cardio(client, headers, discipline="boxing", days_ago=5, duration_minutes=90)

    response = client.get("/stats/cardio", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["totalDurationMinutes"] == 135
    assert len(data["byDiscipline"]) == 2
    running = next(item for item in data["byDiscipline"] if item["discipline"] == "running")
    assert running["durationMinutes"] == 45
    assert running["avgDurationMinutes"] == 45.0


def test_progress_reports_plateau_insight(client: TestClient) -> None:
    headers = _headers(client)
    for days_ago in (2, 9, 16):
        _create_gym(client, headers, days_ago=days_ago, name="press banca", weight_kg=80)

    response = client.get("/stats/progress", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["current"]["sessions"] == 3
    assert data["previous"]["sessions"] == 0
    assert data["volumeDeltaPct"] is None
    kinds = [insight["kind"] for insight in data["insights"]]
    assert "plateau" in kinds


def test_progress_compares_previous_period(client: TestClient) -> None:
    headers = _headers(client)
    _create_gym(client, headers, days_ago=5, name="press banca", weight_kg=80)
    _create_gym(client, headers, days_ago=40, name="press banca", weight_kg=60)

    response = client.get("/stats/progress", headers=headers)
    data = response.json()
    assert data["current"]["sessions"] == 1
    assert data["previous"]["sessions"] == 1
    assert data["sessionDeltaPct"] == 0
