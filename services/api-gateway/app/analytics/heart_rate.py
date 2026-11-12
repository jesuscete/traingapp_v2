"""Frecuencia cardiaca (M6): zonas, TRIMP y kcal por FC. Funciones puras.

- FC máxima estimada: Tanaka (208 − 0,7·edad), más precisa que 220 − edad.
- Zonas por reserva de FC (Karvonen): Z1 50-60 %, Z2 60-70, Z3 70-80, Z4 80-90, Z5 90-100.
- TRIMP de Banister: minutos x reserva x factor exponencial (pondera más la alta intensidad).
- Kcal por FC: Keytel et al. (2005), más precisa que los MET cuando hay pulsómetro.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Sex = Literal["male", "female"] | None

DEFAULT_RESTING_HR = 60
ZONE_BOUNDS = (0.50, 0.60, 0.70, 0.80, 0.90)  # inicio de Z1..Z5 en % de la reserva
MAX_GAP_SECONDS = 30  # huecos mayores (pausas) no cuentan como tiempo en zona


def estimate_max_hr(age: int) -> int:
    return round(208 - 0.7 * age)


@dataclass(frozen=True)
class HeartRateProfile:
    max_hr: int
    resting_hr: int
    max_estimated: bool
    resting_estimated: bool


def hr_profile(max_hr: int | None, resting_hr: int | None, age: int | None) -> HeartRateProfile:
    estimated_max = max_hr is None
    return HeartRateProfile(
        max_hr=max_hr if max_hr is not None else estimate_max_hr(age if age is not None else 35),
        resting_hr=resting_hr if resting_hr is not None else DEFAULT_RESTING_HR,
        max_estimated=estimated_max,
        resting_estimated=resting_hr is None,
    )


def zone_bounds(profile: HeartRateProfile) -> list[tuple[int, int]]:
    """Límites en ppm de Z1..Z5 (Karvonen)."""
    reserve = profile.max_hr - profile.resting_hr
    starts = [round(profile.resting_hr + f * reserve) for f in ZONE_BOUNDS]
    ends = starts[1:] + [profile.max_hr]
    return list(zip(starts, ends, strict=True))


def _reserve_fraction(hr: float, profile: HeartRateProfile) -> float:
    reserve = profile.max_hr - profile.resting_hr
    return max(0.0, min(1.0, (hr - profile.resting_hr) / reserve)) if reserve > 0 else 0.0


def _intervals(times: Sequence[float], hrs: Sequence[float | None]) -> list[tuple[float, float]]:
    """(segundos, ppm) de cada tramo entre muestras válidas consecutivas."""
    out: list[tuple[float, float]] = []
    for i in range(1, len(times)):
        hr = hrs[i]
        dt = times[i] - times[i - 1]
        if hr is not None and hr > 0 and 0 < dt <= MAX_GAP_SECONDS:
            out.append((dt, float(hr)))
    return out


def time_in_zones(
    times: Sequence[float], hrs: Sequence[float | None], profile: HeartRateProfile
) -> list[float]:
    """Segundos en Z1..Z5 (por debajo de Z1 no se cuenta)."""
    zones = [0.0] * 5
    for dt, hr in _intervals(times, hrs):
        fraction = _reserve_fraction(hr, profile)
        index = sum(1 for bound in ZONE_BOUNDS if fraction >= bound) - 1
        if index >= 0:
            zones[index] += dt
    return [round(z) for z in zones]


def trimp(
    times: Sequence[float], hrs: Sequence[float | None], profile: HeartRateProfile, sex: Sex
) -> float:
    """TRIMP de Banister: Σ min · HRr · 0,64·e^(1,92·HRr) (mujeres: 0,86·e^(1,67·HRr))."""
    a, b = (0.86, 1.67) if sex == "female" else (0.64, 1.92)
    total = 0.0
    for dt, hr in _intervals(times, hrs):
        fraction = _reserve_fraction(hr, profile)
        total += dt / 60 * fraction * a * math.exp(b * fraction)
    return round(total, 1)


def keytel_kcal(avg_hr: float, weight_kg: float, age: int, sex: Sex, minutes: float) -> float:
    """Gasto por FC (Keytel 2005). Sin sexo: media de ambas ecuaciones."""
    male = (-55.0969 + 0.6309 * avg_hr + 0.1988 * weight_kg + 0.2017 * age) / 4.184
    female = (-20.4022 + 0.4472 * avg_hr - 0.1263 * weight_kg + 0.074 * age) / 4.184
    per_min = {"male": male, "female": female}.get(sex or "", (male + female) / 2)
    return round(max(0.0, per_min) * minutes, 1)
