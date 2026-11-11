from datetime import UTC, datetime

from app.analytics.records import (
    SessionPerformance,
    SetPerformance,
    compute_records,
    estimated_1rm,
    progress_point,
)


def _perf(day: int, sets: list[SetPerformance]) -> SessionPerformance:
    return SessionPerformance(str(day), datetime(2026, 9, day, tzinfo=UTC), sets)


def test_estimated_1rm_epley_and_limits() -> None:
    assert estimated_1rm(100, 1) == 100
    assert estimated_1rm(100, 5) == 116.7
    assert estimated_1rm(100, 13) is None
    assert estimated_1rm(None, 5) is None
    assert estimated_1rm(0, 5) is None


def test_records_ignore_warmups_and_pick_bests() -> None:
    history = [
        _perf(
            1,
            [SetPerformance(10, 60, is_warmup=True), SetPerformance(5, 80), SetPerformance(5, 80)],
        ),
        _perf(8, [SetPerformance(3, 90), SetPerformance(12, 50)]),
    ]
    rec = compute_records(history)
    assert rec.max_weight_kg == 90
    assert rec.best_e1rm_kg == 99.0
    assert rec.max_reps == 12
    assert rec.best_set_volume_kg == 600
    assert rec.best_session_volume_kg == 870


def test_progress_point_without_data() -> None:
    point = progress_point(_perf(2, [SetPerformance(None, None)]))
    assert (point.best_e1rm_kg, point.top_weight_kg, point.volume_kg) == (None, None, 0.0)
    assert compute_records([]).max_weight_kg is None


def test_translated_details_merges_by_source_id() -> None:
    from app.analytics.catalog_seed import translated_details

    translations = {"Bench": {"nameEs": "Press de banca", "instructionsEs": ["Túmbate."]}}
    merged = translated_details({"sourceId": "Bench", "level": "beginner"}, translations)
    assert merged == {
        "sourceId": "Bench",
        "level": "beginner",
        "nameEs": "Press de banca",
        "instructionsEs": ["Túmbate."],
    }
    assert translated_details({"sourceId": "Other"}, translations) is None
    assert translated_details(merged, translations) is None
