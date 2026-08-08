from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.analytics import calibration as calibration_analytics


def _register(client: TestClient, email: str = "calib@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Calib"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace(
        "+00:00", "Z"
    )


def _boxing_session(
    client: TestClient, headers: dict[str, str], *, days_ago: int
) -> None:
    response = client.post(
        "/sessions",
        json={
            "discipline": "boxing",
            "rawText": "boxing session",
            "performedAt": _iso(days_ago),
            "durationMinutes": 60,
            "details": {"strikes": 1500, "rpe": 8},
            "exercises": [],
        },
        headers=headers,
    )
    assert response.status_code == 201


def _report_doms(
    client: TestClient, headers: dict[str, str], *, days_ago: int, pain: int
) -> None:
    response = client.post(
        "/stats/doms",
        json={
            "date": (datetime.now(UTC) - timedelta(days=days_ago)).date().isoformat(),
            "entries": [
                {"muscleGroup": "shoulders", "pain": pain},
                {"muscleGroup": "quadriceps", "pain": 2},
            ],
        },
        headers=headers,
    )
    assert response.status_code == 200


def test_gradient_step_direction() -> None:
    step = calibration_analytics.gradient_step(
        {"shoulders": 30.0, "quadriceps": 80.0}, {"shoulders": 9, "quadriceps": 2}
    )
    # Mas dolor que el predicho -> paso positivo; menos dolor -> negativo.
    assert step["shoulders"] > 0
    assert step["quadriceps"] < 0


def test_apply_gradient_accumulates_and_clamps() -> None:
    ng = calibration_analytics.apply_gradient(
        {"shoulders": 0.1}, {"shoulders": 0.1}
    )
    assert ng["shoulders"] > 0.1
    # Cota acumulada.
    ng_max = calibration_analytics.apply_gradient(
        {"shoulders": 0.4}, {"shoulders": 0.15}
    )
    assert ng_max["shoulders"] <= calibration_analytics.NG_DELTA_MAX


def test_ng_factor_and_tau2() -> None:
    assert calibration_analytics.ng_factor(0.2) == 1.2
    assert calibration_analytics.ng_factor(-2.0) >= 0.05
    factors = calibration_analytics.tau2_factor_from({"shoulders": 0.2})
    assert factors["shoulders"] > 1.0
    assert calibration_analytics.tau2_factor_from({"chest": 0.0})["chest"] == 1.0


def test_pearson() -> None:
    assert calibration_analytics.pearson([]) is None
    assert calibration_analytics.pearson([(1.0, 2.0)]) is None
    assert abs(calibration_analytics.pearson([(1.0, 2.0), (2.0, 4.0), (3.0, 6.0)]) - 1.0) < 0.01


def test_confidence_level_thresholds() -> None:
    assert calibration_analytics.confidence_level(0) == "baja"
    assert calibration_analytics.confidence_level(5) == "media"
    assert calibration_analytics.confidence_level(10) == "alta"


def test_calibration_apply_and_get(client: TestClient) -> None:
    headers = _register(client)
    # Sesion de boxeo hace 2 dias: fatiga alta predicha en hombros al dia siguiente.
    _boxing_session(client, headers, days_ago=2)
    _report_doms(client, headers, days_ago=0, pain=9)

    response = client.post("/stats/calibration", headers=headers)
    assert response.status_code == 200
    body = response.json()
    by_group = {item["muscleGroup"]: item for item in body["groups"]}
    # Mas dolor del predicho en hombros -> ng_delta positivo persistido.
    assert by_group["shoulders"]["ngDelta"] > 0
    assert by_group["shoulders"]["sampleCount"] >= 1
    assert by_group["shoulders"]["tau2Factor"] > 1.0
    assert by_group["shoulders"]["reportedDoms"] == 9

    # GET devuelve el estado persistido.
    fetched = client.get("/stats/calibration", headers=headers)
    assert fetched.status_code == 200
    fetched_groups = {item["muscleGroup"]: item for item in fetched.json()["groups"]}
    assert (
        fetched_groups["shoulders"]["ngDelta"]
        == by_group["shoulders"]["ngDelta"]
    )


def test_calibration_requires_auth(client: TestClient) -> None:
    assert client.get("/stats/calibration").status_code == 401
    assert client.post("/stats/calibration").status_code == 401
