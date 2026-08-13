from datetime import UTC, datetime, timedelta

from app.analytics.weight_suggestion import WeightRecord, suggest_weight


def _record(set_number: int, weight: float, days_ago: int) -> WeightRecord:
    return WeightRecord(
        set_number=set_number,
        weight=weight,
        performed_at=datetime.now(UTC) - timedelta(days=days_ago),
    )


def test_empty_history_returns_none() -> None:
    assert suggest_weight([], set_number=1) is None


def test_prefers_same_set_number_latest() -> None:
    history = [
        _record(1, 70.0, days_ago=30),
        _record(2, 82.5, days_ago=30),
        _record(1, 72.5, days_ago=7),
    ]
    assert suggest_weight(history, set_number=1) == 72.5


def test_falls_back_to_latest_of_exercise() -> None:
    history = [
        _record(1, 70.0, days_ago=30),
        _record(2, 82.5, days_ago=7),
    ]
    assert suggest_weight(history, set_number=3) == 82.5


def test_tie_break_by_performed_at() -> None:
    history = [
        _record(1, 80.0, days_ago=14),
        _record(1, 85.0, days_ago=3),
    ]
    assert suggest_weight(history, set_number=1) == 85.0


def test_single_record() -> None:
    assert suggest_weight([_record(4, 60.0, days_ago=1)], set_number=4) == 60.0
