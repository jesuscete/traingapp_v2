from datetime import UTC, datetime, timedelta

from app.analytics import periods
from app.models import TrainingSession


def _session(
    discipline: str,
    days_ago: int,
    *,
    duration_minutes: int = 60,
    volume_kg: float = 100,
    kcal: float = 300,
) -> TrainingSession:
    return TrainingSession(
        discipline=discipline,
        raw_text="test",
        performed_at=datetime.now(UTC) - timedelta(days=days_ago),
        duration_minutes=duration_minutes,
        volume_kg=volume_kg,
        estimated_kcal=kcal,
    )


def test_previous_period_same_duration() -> None:
    start = datetime(2026, 1, 10, tzinfo=UTC)
    end = datetime(2026, 1, 17, tzinfo=UTC)
    prev_start, prev_end = periods.previous_period(start, end)
    assert (prev_start, prev_end) == (
        datetime(2026, 1, 3, tzinfo=UTC),
        datetime(2026, 1, 10, tzinfo=UTC),
    )


def test_previous_period_month_window() -> None:
    start = datetime(2026, 3, 1, tzinfo=UTC)
    end = datetime(2026, 3, 31, tzinfo=UTC)
    prev_start, prev_end = periods.previous_period(start, end)
    assert prev_end - prev_start == end - start
    assert prev_end == start


def test_period_range() -> None:
    now = datetime(2026, 1, 20, 12, 0, tzinfo=UTC)
    start, end = periods.period_range(7, now)
    assert end == now
    assert start == now - timedelta(days=7)


def test_discipline_totals_aggregates() -> None:
    sessions = [
        _session("gym", 0, duration_minutes=60, volume_kg=500, kcal=400),
        _session("gym", 1, duration_minutes=90, volume_kg=300, kcal=500),
        _session("running", 2, duration_minutes=45, volume_kg=0, kcal=350),
    ]
    totals = periods.discipline_totals(sessions)
    by_name = {item.discipline: item for item in totals}

    assert by_name["gym"].sessions == 2
    assert by_name["gym"].duration_minutes == 150
    assert by_name["gym"].volume_kg == 800
    assert by_name["gym"].estimated_kcal == 900
    assert by_name["running"].sessions == 1
    assert by_name["running"].duration_minutes == 45


def test_deltas_positive_and_negative() -> None:
    current = [
        _session("boxing", 0),
        _session("boxing", 1),
        _session("running", 2),
        _session("swimming", 3),
    ]
    previous = [
        _session("boxing", 3),
        _session("running", 4),
        _session("running", 5),
        _session("climbing", 6),
    ]
    deltas = {
        item.discipline: item.delta_pct
        for item in periods.compute_discipline_deltas(current, previous, top_n=4)
    }

    assert deltas["boxing"] == 100.0
    assert deltas["running"] == -50.0
    assert deltas["climbing"] == -100.0
    assert deltas["swimming"] is None  # actividad nueva
    assert len(deltas) == 4


def test_deltas_top_n_sorted_by_abs() -> None:
    current = [
        _session("gym", 0, duration_minutes=10),
        _session("running", 1),
        _session("boxing", 2),
    ]
    previous = [
        _session("gym", 3, duration_minutes=10),
        _session("gym", 4, duration_minutes=10),
        _session("running", 5),
    ]
    result = periods.compute_discipline_deltas(current, previous, top_n=2)
    assert len(result) == 2
    # gym pasa de 2 a 1 (-50%), boxing aparece (None), running sin cambio (0%)
    assert result[0].discipline == "gym"
    assert result[1].discipline == "boxing"


def test_deltas_empty_periods() -> None:
    assert periods.compute_discipline_deltas([], []) == []
