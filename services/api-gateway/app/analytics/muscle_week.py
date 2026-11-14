"""Carga por músculo de los últimos 7 días y su reparto (qué se ha entrenado de más / de menos).

Parte de los impulsos diarios del motor de fatiga, que ya traducen cualquier deporte
(gimnasio, HYROX, boxeo, carrera…) a carga por grupo muscular.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Level = Literal["high", "ok", "low", "none"]

WINDOW_DAYS = 7
# Grupos pequeños que casi nunca reciben carga directa: no se señalan como «carga baja».
MINOR_GROUPS = frozenset({"neck", "forearms"})
HIGH_FACTOR = 1.4  # ≥ 1,4× la media de los grupos principales
LOW_FACTOR = 0.35  # ≤ 0,35× la media
MAX_FLAGGED = 3
MIN_TOTAL = 1.0  # por debajo, la semana no tiene carga suficiente para opinar


@dataclass(frozen=True)
class MuscleLoad:
    group: str
    load: float
    relative: float  # 0-1 respecto al grupo más cargado
    level: Level


@dataclass(frozen=True)
class MuscleWeek:
    muscles: list[MuscleLoad]
    high: list[str]
    low: list[str]


def weekly_loads(
    impulses: dict[date, dict[str, float]], today: date, groups: list[str]
) -> dict[str, float]:
    return {
        g: sum(
            impulses.get(today - timedelta(days=offset), {}).get(g, 0.0)
            for offset in range(WINDOW_DAYS)
        )
        for g in groups
    }


def classify(loads: dict[str, float]) -> MuscleWeek:
    total = sum(loads.values())
    top = max(loads.values(), default=0.0)
    if total < MIN_TOTAL or top <= 0:
        return MuscleWeek(
            muscles=[MuscleLoad(g, round(v, 1), 0.0, "none") for g, v in loads.items()],
            high=[],
            low=[],
        )
    major = [v for g, v in loads.items() if g not in MINOR_GROUPS]
    mean = sum(major) / len(major) if major else total / len(loads)

    def level(group: str, value: float) -> Level:
        if value >= mean * HIGH_FACTOR:
            return "high"
        if group not in MINOR_GROUPS and value <= mean * LOW_FACTOR:
            return "low"
        return "ok"

    muscles = [MuscleLoad(g, round(v, 1), round(v / top, 3), level(g, v)) for g, v in loads.items()]
    high = sorted((m for m in muscles if m.level == "high"), key=lambda m: -m.load)
    low = sorted((m for m in muscles if m.level == "low"), key=lambda m: m.load)
    return MuscleWeek(
        muscles=muscles,
        high=[m.group for m in high[:MAX_FLAGGED]],
        low=[m.group for m in low[:MAX_FLAGGED]],
    )
