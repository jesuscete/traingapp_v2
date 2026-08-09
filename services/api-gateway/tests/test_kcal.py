from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.analytics import kcal as kcal_analytics


def _register(client: TestClient, email: str = "kcal@example.com") -> dict[str, str]:
    response = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Kcal"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace(
        "+00:00", "Z"
    )


def _cardio_input(
    *, rpe: int | None = None, avg_hr: float | None = None
) -> kcal_analytics.SessionKcalInput:
    return kcal_analytics.SessionKcalInput(
        discipline="running",
        weight_kg=70.0,
        duration_minutes=60,
        rpe=rpe,
        avg_heart_rate=avg_hr,
    )


def _gym_input(weight_kg: float | None = 60.0) -> kcal_analytics.SessionKcalInput:
    return kcal_analytics.SessionKcalInput(
        discipline="gym",
        weight_kg=75.0,
        duration_minutes=60,
        rpe=8,
        exercises=(
            kcal_analytics.ExerciseInput(
                name="press banca",
                weight_kg=weight_kg,
                sets=3,
                reps=10,
                rest_seconds=60,
            ),
        ),
    )


def test_cardio_base_matches_met() -> None:
    result = kcal_analytics.estimate(_cardio_input())
    # Sin RPE ni HR: 8.2 MET x 70 kg x 1h = 574.
    assert abs(result.kcal - 8.2 * 70) < 1
    assert result.confidence > 0.4  # peso + duracion


def test_rpe_increases_kcal() -> None:
    light = kcal_analytics.estimate(_cardio_input(rpe=5))
    hard = kcal_analytics.estimate(_cardio_input(rpe=10))
    assert hard.kcal > light.kcal


def test_heart_rate_increases_kcal() -> None:
    low = kcal_analytics.estimate(_cardio_input(avg_hr=110))
    high = kcal_analytics.estimate(_cardio_input(avg_hr=165))
    assert high.kcal > low.kcal


def test_cardio_without_duration_is_none() -> None:
    result = kcal_analytics.estimate(
        kcal_analytics.SessionKcalInput(
            discipline="boxing", weight_kg=70.0, duration_minutes=None
        )
    )
    assert result.kcal is None


def test_gym_mechanical_work_increases_with_volume() -> None:
    light = kcal_analytics.estimate(_gym_input(weight_kg=40.0))
    heavy = kcal_analytics.estimate(_gym_input(weight_kg=100.0))
    assert heavy.kcal > light.kcal
    assert heavy.kcal > 0
    # El trabajo mecanico aporta: 100 kg * 30 reps * 9.81 * 0.5 m / 1000 / 4.184 / 0.22
    assert heavy.kcal > 100 * 30 * 9.81 * 0.5 / 1000 / 4.184 / 0.22


def test_gym_without_any_data_is_none() -> None:
    result = kcal_analytics.estimate(
        kcal_analytics.SessionKcalInput(
            discipline="gym", weight_kg=None, duration_minutes=None, exercises=()
        )
    )
    assert result.kcal is None


def test_confidence_high_with_rich_cardio() -> None:
    result = kcal_analytics.estimate(
        _cardio_input(rpe=8, avg_hr=150)
    )
    assert result.confidence_level == "alta"
    assert any("intensidad alta" in f for f in result.factors)


def test_confidence_low_without_data() -> None:
    result = kcal_analytics.estimate(
        kcal_analytics.SessionKcalInput(
            discipline="running", weight_kg=None, duration_minutes=60
        )
    )
    assert result.confidence_level == "baja"
    assert result.kcal is None
    assert len(result.factors) > 0


def test_session_api_stores_confidence_and_factors(client: TestClient) -> None:
    headers = _register(client)
    client.put("/profile", headers=headers, json={"weightKg": 75})
    response = client.post(
        "/sessions",
        json={
            "discipline": "gym",
            "rawText": "press banca",
            "performedAt": _iso(0),
            "durationMinutes": 60,
            "details": {"rpe": 8},
            "exercises": [
                {
                    "name": "press banca",
                    "sets": 3,
                    "reps": 10,
                    "weightKg": 80,
                    "details": {"restSeconds": 60},
                }
            ],
        },
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["estimatedKcal"] is not None
    assert data["estimatedKcal"] > 0
    assert data["details"]["kcal_confidence_level"] in ("alta", "media", "baja")
    assert isinstance(data["details"]["kcal_factors"], list)
    assert len(data["details"]["kcal_factors"]) > 0
