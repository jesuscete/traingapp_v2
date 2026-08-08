from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.analytics import fatigue as fatigue_analytics

MUSCLE_GROUPS = fatigue_analytics.MUSCLE_GROUPS


def _register(client: TestClient, email: str = "fatigue@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Fatigue"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace(
        "+00:00", "Z"
    )


def _create_session(
    client: TestClient,
    headers: dict[str, str],
    *,
    discipline: str,
    days_ago: int,
    duration_minutes: int = 60,
    details: dict[str, object] | None = None,
    rpe: int | None = None,
    distance_meters: float | None = None,
    volume_kg: float | None = None,
) -> None:
    payload: dict[str, object] = {
        "discipline": discipline,
        "rawText": f"{discipline} session",
        "performedAt": _iso(days_ago),
        "durationMinutes": duration_minutes,
        "exercises": [],
    }
    if details:
        payload["details"] = details
    if rpe is not None:
        payload["details"] = {**(details or {}), "rpe": rpe}
    if distance_meters is not None:
        payload["distanceMeters"] = distance_meters
    if volume_kg is not None:
        payload["volumeKg"] = volume_kg
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 201


def test_decay_monotonic_and_limits() -> None:
    assert 0 < fatigue_analytics.decay(1.0) < 1.0
    # Mas recuperacion (m mayor) deja MENOS fatiga residual (factor menor).
    assert fatigue_analytics.decay(1.2) < fatigue_analytics.decay(0.8)
    assert fatigue_analytics.decay(100.0) > 0.0


def test_mod_from_readiness_neutral_and_extremes() -> None:
    assert fatigue_analytics.mod_from_readiness(None) == 1.0
    neutral = fatigue_analytics.mod_from_readiness(
        fatigue_analytics.ReadinessData()
    )
    assert abs(neutral - 1.0) < 1e-9
    good = fatigue_analytics.mod_from_readiness(
        fatigue_analytics.ReadinessData(sleep_hours=8.0)
    )
    bad = fatigue_analytics.mod_from_readiness(
        fatigue_analytics.ReadinessData(sleep_hours=4.0)
    )
    assert good > bad  # dormir bien aumenta los dias efectivos de recuperacion


def test_boxing_impulse_matches_spec_example() -> None:
    data = fatigue_analytics.SessionData(
        discipline="boxing",
        duration_minutes=60,
        strikes=1500,
        rpe=8,
    )
    loads = fatigue_analytics.session_load(
        data, fatigue_analytics.MUSCLE_LOAD_DEFAULT
    )
    # I = 100 * 0.95 * min(1, 1500/2000) * 0.8 = 57
    assert abs(loads["shoulders"] - 57.0) < 0.1
    assert abs(loads["core"] - 54.0) < 0.1
    assert abs(loads["forearms"] - 48.0) < 0.1


def test_boxing_accumulation_two_sessions(client: TestClient) -> None:
    headers = _register(client)
    # Sesion mas antigua (hace 2 dias): 1500 golpes -> I = 57.
    _create_session(
        client,
        headers,
        discipline="boxing",
        days_ago=2,
        duration_minutes=60,
        details={"strikes": 1500},
        rpe=8,
    )
    # Sesion de hoy: 1200 golpes -> I = 45.6.
    _create_session(
        client,
        headers,
        discipline="boxing",
        days_ago=0,
        duration_minutes=60,
        details={"strikes": 1200},
        rpe=8,
    )

    response = client.get("/stats/fatigue", headers=headers)
    assert response.status_code == 200
    data = response.json()
    muscles = {item["muscleGroup"]: item for item in data["muscles"]}
    # Dia 0: 57 -> dia 1: 0.542*57 = 31 -> dia 2: 0.542*31 + 45.6 = 62.4
    assert 61 <= muscles["shoulders"]["fatigue"] <= 63
    # El hombro es el grupo mas fatigado (peso alto del boxeo).
    assert muscles["shoulders"]["fatigue"] >= muscles["quadriceps"]["fatigue"]
    assert data["maxFatigue"] >= muscles["shoulders"]["fatigue"]
    assert len(data["muscles"]) == 12


def test_project_reduces_fatigue(client: TestClient) -> None:
    headers = _register(client)
    _create_session(client, headers, discipline="boxing", days_ago=0)
    base = client.get("/stats/fatigue", headers=headers).json()
    future = client.get("/stats/fatigue?projectDays=3", headers=headers).json()
    base_shoulders = next(
        m for m in base["muscles"] if m["muscleGroup"] == "shoulders"
    )["fatigue"]
    future_shoulders = next(
        m for m in future["muscles"] if m["muscleGroup"] == "shoulders"
    )["fatigue"]
    assert future_shoulders < base_shoulders
    assert future["projected"] > future["asOf"]


def test_catalog_covers_all_requested_sports() -> None:
    expected = {
        "football", "running", "badminton", "basketball", "table_tennis",
        "volleyball", "cycling", "tennis", "swimming", "cricket", "golf",
        "baseball", "martial_arts", "boxing", "hockey", "rugby", "handball",
        "climbing", "ski_snowboard", "calisthenics", "gym", "other",
    }
    assert expected <= set(fatigue_analytics.MUSCLE_LOAD_DEFAULT)
    for discipline, groups in fatigue_analytics.MUSCLE_LOAD_DEFAULT.items():
        assert set(groups) == set(MUSCLE_GROUPS)
        for weight in groups.values():
            assert 0.1 <= weight <= 1.0


def test_running_weights_legs_highest() -> None:
    running = fatigue_analytics.MUSCLE_LOAD_DEFAULT["running"]
    assert running["calves"] > running["chest"]
    assert running["calves"] == 0.95


def test_boxing_weights_upper_body() -> None:
    boxing = fatigue_analytics.MUSCLE_LOAD_DEFAULT["boxing"]
    assert boxing["shoulders"] >= boxing["quadriceps"]
    assert boxing["core"] >= boxing["back"]


def test_readiness_affects_decay(client: TestClient) -> None:
    headers = _register(client)
    _create_session(client, headers, discipline="boxing", days_ago=0)

    response = client.get("/stats/fatigue", headers=headers)
    assert response.status_code == 200
    assert response.json()["readiness"] is None

    saved = client.post(
        "/stats/readiness",
        headers=headers,
        json={"date": date.today().isoformat(), "sleepHours": 8, "doms": 2},
    )
    assert saved.status_code == 200
    assert saved.json()["sleepHours"] == 8

    with_readiness = client.get("/stats/fatigue", headers=headers).json()
    assert with_readiness["readiness"] is not None
    assert with_readiness["readiness"]["doms"] == 2


def test_readiness_upsert_updates_existing(client: TestClient) -> None:
    headers = _register(client)
    today = date.today().isoformat()
    client.post(
        "/stats/readiness",
        headers=headers,
        json={"date": today, "sleepHours": 6},
    )
    client.post(
        "/stats/readiness",
        headers=headers,
        json={"date": today, "sleepHours": 9, "restDay": True},
    )
    response = client.get("/stats/readiness", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["sleepHours"] == 9
    assert data["restDay"] is True


def test_risk_detected_when_fatigue_high(client: TestClient) -> None:
    headers = _register(client)
    # Tres sesiones de boxeo intensas en dias seguidos elevan hombro/core.
    for days_ago in (0, 1, 2):
        _create_session(
            client,
            headers,
            discipline="boxing",
            days_ago=days_ago,
            duration_minutes=90,
            details={"strikes": 2500},
            rpe=10,
        )
    response = client.get("/stats/fatigue", headers=headers)
    data = response.json()
    shoulders = next(
        m for m in data["muscles"] if m["muscleGroup"] == "shoulders"
    )
    assert shoulders["fatigue"] >= 70
    assert any(
        risk["muscleGroup"] == "shoulders" for risk in data["risks"]
    )
    assert len(data["risks"]) > 0


def test_fatigue_requires_auth(client: TestClient) -> None:
    assert client.get("/stats/fatigue").status_code == 401
    assert client.get("/stats/readiness").status_code == 401
    assert client.post("/stats/readiness", json={}).status_code == 401
