import pytest

from app.analytics.strength import estimated_1rm, percent_of_1rm

# Mismos vectores que services/web/lib/strength.ts (mantener sincronizados).
VECTORS = [
    # (peso, reps, rpe, 1RM esperado)
    (100, 1, None, 100.0),
    (100, 5, None, 115.9),  # 86,3 %
    (100, 3, None, 108.5),  # 92,2 %
    (100, 10, None, 135.3),  # 73,9 %
    (100, 5, 8, 123.3),  # 81,1 %
    (100, 8, 7, 141.4),  # 70,7 %
    (100, 1, 9, 104.7),  # 95,5 %
    (80, 12, 10, 117.6),  # 68,0 %
]


@pytest.mark.parametrize(("weight", "reps", "rpe", "expected"), VECTORS)
def test_rpe_chart_vectors(weight: float, reps: int, rpe: float | None, expected: float) -> None:
    assert estimated_1rm(weight, reps, rpe) == expected


def test_limits() -> None:
    assert estimated_1rm(100, 13) is None
    assert estimated_1rm(100, 0) is None
    assert estimated_1rm(None, 5) is None
    assert estimated_1rm(0, 5) is None
    assert percent_of_1rm(5, 4) == percent_of_1rm(5, 6)  # RPE por debajo de 6 se acota


def test_matches_classic_formulas_at_failure() -> None:
    # A RPE 10 la tabla queda a ±2,5 kg de Brzycki/Epley: no rompe los históricos.
    for reps in range(2, 11):
        chart = estimated_1rm(100, reps)
        assert chart is not None
        brzycki = 100 * 36 / (37 - reps)
        epley = 100 * (1 + reps / 30)
        assert min(brzycki, epley) - 2.5 <= chart <= max(brzycki, epley) + 2.5
