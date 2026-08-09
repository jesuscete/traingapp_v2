from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.analytics import fatigue as fatigue_analytics

MUSCLE_GROUPS = fatigue_analytics.MUSCLE_GROUPS


def _register(client: TestClient, email: str = "load@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Load"},
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
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 201


def test_mod_for_group_doms_penalizes_only_group() -> None:
    readiness = fatigue_analytics.ReadinessData(doms=2, sleep_hours=7.0)
    base = fatigue_analytics.mod_from_readiness(readiness)
    with_doms = fatigue_analytics.mod_for_group(
        readiness, {"shoulders": 10}, "shoulders"
    )
    other = fatigue_analytics.mod_for_group(readiness, {"shoulders": 10}, "chest")
    # El grupo con dolor (10) recupera MENOS (m menor) que el global con doms=2.
    assert with_doms < base
    # Un grupo sin dolor en el mapa mantiene el m global.
    assert abs(other - base) < 1e-9
    # El grupo con dolor deja MAS fatiga residual al dia siguiente.
    assert fatigue_analytics.decay(with_doms) > fatigue_analytics.decay(base)


def test_fatigue_projection_next_72h(client: TestClient) -> None:
    headers = _register(client)
    _create_session(
        client, headers, discipline="boxing", days_ago=0, rpe=8, details={"strikes": 1500}
    )

    response = client.get("/stats/fatigue", headers=headers)
    assert response.status_code == 200
    projection = response.json()["projection"]
    assert len(projection) == 3
    days_ahead = [item["daysAhead"] for item in projection]
    assert days_ahead == [1, 2, 3]
    # Sin nuevas cargas, la fatiga media proyectada decrece con los dias.
    averages = [item["avgFatigue"] for item in projection]
    assert averages[0] > averages[1] > averages[2]


def test_fatigue_series_daily_by_group(client: TestClient) -> None:
    headers = _register(client)
    _create_session(
        client, headers, discipline="boxing", days_ago=0, rpe=8, details={"strikes": 1200}
    )
    _create_session(
        client, headers, discipline="running", days_ago=1, duration_minutes=45, rpe=6
    )

    response = client.get("/stats/fatigue/series?days=30", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["periodDays"] == 30
    assert len(body["series"]) >= 1
    today = next(
        item
        for item in body["series"]
        if item["date"] == datetime.now(UTC).date().isoformat()
    )
    assert len(today["muscles"]) == 12
    # El boxeo fatiga mas el hombro que el running.
    by_group = {m["muscleGroup"]: m["fatigue"] for m in today["muscles"]}
    assert by_group["shoulders"] > by_group["quadriceps"]


def test_load_analysis_monotony_strain(client: TestClient) -> None:
    headers = _register(client)
    # Carga alta hoy, ninguna antes -> monotonia baja (variabilidad alta).
    _create_session(client, headers, discipline="gym", days_ago=0, duration_minutes=70, rpe=9)
    _create_session(client, headers, discipline="gym", days_ago=7, duration_minutes=70, rpe=8)

    response = client.get("/stats/load?days=30", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["periodDays"] == 30
    assert body["totalLoad"] > 0
    assert body["monotony"] > 0
    assert body["strain"] > 0
    assert len(body["byMuscleGroup"]) == 12
    for item in body["byMuscleGroup"]:
        assert item["muscleGroup"] in MUSCLE_GROUPS
        assert item["accumulatedLoad"] >= 0
        assert 0 <= item["recovery"] <= 100
        assert item["trend"] in ("increasing", "stable", "decreasing")


def test_load_requires_auth(client: TestClient) -> None:
    assert client.get("/stats/load").status_code == 401
    assert client.get("/stats/fatigue/series").status_code == 401
