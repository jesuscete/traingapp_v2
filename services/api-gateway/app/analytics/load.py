"""Analisis de carga de entrenamiento (Banister): monotonia y strain.

- Carga diaria: suma de impulsos de sesion del dia (por grupo o global).
- Monotonia = media / desviacion tipica de la carga diaria.
- Strain = carga total del periodo x monotonia.

Determinista (ADR-006/013); opera sobre los impulsos ya calculados por
`app.analytics.fatigue.simulate`.
"""

from datetime import date

from app.analytics.fatigue import MUSCLE_GROUPS


def daily_loads(
    impulses: dict[date, dict[str, float]],
    group: str | None = None,
) -> list[float]:
    """Cargas diarias del periodo (todas las fechas presentes en `impulses`)."""
    if group is not None:
        return [round(day.get(group, 0.0), 1) for day in impulses.values()]
    return [round(sum(day.values()), 1) for day in impulses.values()]


def monotony(loads: list[float]) -> float:
    """Media / desv. tipica de la carga diaria (1.0 si no hay variacion)."""
    if not loads:
        return 0.0
    mean = sum(loads) / len(loads)
    if mean <= 0:
        return 0.0
    if len(loads) == 1:
        return 1.0
    variance = sum((value - mean) ** 2 for value in loads) / len(loads)
    std = variance**0.5
    if std == 0:
        return 1.0
    return float(round(mean / std, 2))


def strain(loads: list[float]) -> float:
    """Carga total del periodo x monotonia (indice de desgaste global)."""
    if not loads:
        return 0.0
    return round(sum(loads) * monotony(loads), 1)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def trend(loads: list[float]) -> str:
    """Tendencia de la carga: compara el ultimo tercio vs el primer tercio.

    >10% up -> increasing; >10% down -> decreasing; else stable.
    """
    if len(loads) < 3:
        return "stable"
    third = max(1, len(loads) // 3)
    first = _mean(loads[:third])
    last = _mean(loads[-third:])
    if first > 0 and last >= first * 1.10:
        return "increasing"
    if first > 0 and last <= first * 0.90:
        return "decreasing"
    return "stable"


def group_recovery(state: dict[str, float], group: str) -> float:
    """Recuperacion estimada del grupo = 100 - fatiga actual."""
    return round(max(0.0, 100.0 - state.get(group, 0.0)), 1)


def analyse(
    impulses: dict[date, dict[str, float]],
    state_today: dict[str, float],
) -> dict[str, object]:
    """Resumen de carga del periodo (mismo formato que `load-analysis.json`)."""
    loads = daily_loads(impulses)
    by_group = [
        {
            "muscle_group": group,
            "accumulated_load": round(
                sum(day.get(group, 0.0) for day in impulses.values()), 1
            ),
            "recovery": group_recovery(state_today, group),
            "trend": trend(daily_loads(impulses, group)),
        }
        for group in MUSCLE_GROUPS
    ]
    return {
        "total_load": sum(loads),
        "monotony": monotony(loads),
        "strain": strain(loads),
        "by_muscle_group": by_group,
    }
