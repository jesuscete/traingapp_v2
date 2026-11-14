from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.analytics.fatigue import MUSCLE_GROUPS
from app.analytics.muscle_week import classify, weekly_loads
from tests.test_fatigue import _create_session, _register

TODAY = date(2026, 11, 14)


def test_weekly_loads_only_counts_last_7_days() -> None:
    impulses = {
        TODAY: {"chest": 10.0},
        TODAY - timedelta(days=6): {"chest": 5.0},
        TODAY - timedelta(days=7): {"chest": 100.0},
    }
    loads = weekly_loads(impulses, TODAY, ["chest", "back"])
    assert loads == {"chest": 15.0, "back": 0.0}


def test_classify_flags_overloaded_and_neglected_groups() -> None:
    loads = {g: 10.0 for g in MUSCLE_GROUPS}
    loads["shoulders"] = 40.0
    loads["back"] = 1.0
    loads["neck"] = 0.0  # grupo menor: no se señala como bajo
    week = classify(loads)
    assert week.high == ["shoulders"]
    assert week.low == ["back"]
    by_group = {m.group: m for m in week.muscles}
    assert by_group["shoulders"].relative == 1.0
    assert by_group["neck"].level == "ok"


def test_classify_without_load_says_nothing() -> None:
    week = classify({g: 0.0 for g in MUSCLE_GROUPS})
    assert week.high == [] and week.low == []
    assert all(m.level == "none" for m in week.muscles)


def test_muscle_week_endpoint_flags_boxing_shoulders(client: TestClient) -> None:
    headers = _register(client, "muscleweek@example.com")
    _create_session(
        client,
        headers,
        discipline="boxing",
        days_ago=1,
        duration_minutes=60,
        details={"strikes": 1500},
        rpe=8,
    )
    response = client.get("/stats/muscle-week", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["muscles"]) == len(MUSCLE_GROUPS)
    assert "shoulders" in data["high"]
