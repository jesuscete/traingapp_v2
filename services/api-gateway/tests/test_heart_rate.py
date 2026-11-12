from app.analytics.heart_rate import (
    estimate_max_hr,
    hr_profile,
    keytel_kcal,
    time_in_zones,
    trimp,
    zone_bounds,
)

PROFILE = hr_profile(191, 55, 32)


def test_profile_estimates_when_missing() -> None:
    assert estimate_max_hr(32) == 186
    p = hr_profile(None, None, 32)
    assert (p.max_hr, p.resting_hr, p.max_estimated, p.resting_estimated) == (186, 60, True, True)
    assert PROFILE.max_estimated is False


def test_karvonen_zones() -> None:
    # reserva 136: Z1 desde 55+68=123, Z2 55+81,6≈137, Z3 150, Z4 164, Z5 177
    assert zone_bounds(PROFILE) == [(123, 137), (137, 150), (150, 164), (164, 177), (177, 191)]


def test_time_in_zones_and_gaps() -> None:
    times = [0, 10, 20, 30, 40, 400, 410]  # el hueco 40->400 (pausa) no cuenta
    hrs = [140, 140, 155, 170, 180, 180, 100]
    # cada tramo usa la FC al final: 140 Z2, 155 Z3, 170 Z4, 180 Z5; 100 queda por debajo de Z1
    assert time_in_zones(times, hrs, PROFILE) == [0, 10, 10, 10, 10]


def test_trimp_weights_intensity() -> None:
    times = list(range(0, 3601, 5))
    easy = trimp(times, [130] * len(times), PROFILE, "male")
    hard = trimp(times, [170] * len(times), PROFILE, "male")
    assert hard > easy * 2.5  # 1 h en Z4 carga mucho más que 1 h suave
    assert 50 < easy < 70  # 60 min · 0,551 · 0,64 · e^(1,058) ≈ 61


def test_keytel_reference() -> None:
    # (−55,0969 + 0,6309·150 + 0,1988·75 + 0,2017·32) / 4,184 = 14,56 kcal/min -> 873 kcal
    assert round(keytel_kcal(150, 75, 32, "male", 60)) == 873
    assert keytel_kcal(30, 75, 32, "male", 10) == 0.0  # la fórmula daría negativo: se acota a 0
