"""Cálculos de nutrición (M5): funciones puras, sin BD ni IA.

- Gasto basal: Mifflin-St Jeor (la ecuación más precisa para población general).
- Gasto del día = basal x actividad cotidiana (sin entrenos) + kcal reales de los entrenos.
- Objetivo = mantenimiento ± ajuste por objetivo, con límites de seguridad.
- Macros: proteína por kg, grasa mínima, resto en hidratos.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Goal = Literal["perder", "mantener", "ganar", "corte"]
Sex = Literal["male", "female"] | None

KCAL_PER_KG_FAT = 7700.0
DEFAULT_LOSS_KG_WEEK = 0.5
DEFAULT_GAIN_KG_WEEK = 0.25
DEFAULT_CUT_PCT_WEEK = 0.0075  # 0,75 % del peso corporal por semana
MAX_SAFE_PCT_WEEK = 0.01  # más de 1 %/semana: pérdida de músculo y rendimiento
MAX_DEFICIT_SHARE = 0.25  # nunca más del 25 % por debajo de mantenimiento
FAT_MIN_G_PER_KG = 0.8
FAT_MIN_SHARE = 0.20
FIBER_G_PER_1000_KCAL = 14.0


def age_on(birth_year: int, today: date) -> int:
    return today.year - birth_year


def bmr_mifflin(weight_kg: float, height_cm: float, age: int, sex: Sex) -> float:
    """Metabolismo basal (kcal/día). Sin sexo se usa el punto medio de ambas fórmulas."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    offset = {"male": 5.0, "female": -161.0}.get(sex or "", -78.0)
    return round(base + offset, 1)


def scale_per_100g(per_100g: float | None, grams: float) -> float | None:
    return None if per_100g is None else round(per_100g * grams / 100, 1)


@dataclass(frozen=True)
class DailyTarget:
    bmr: float
    daily_activity_kcal: float  # basal x factor (sin entrenos)
    training_kcal: float
    maintenance_kcal: float
    adjustment_kcal: float
    target_kcal: float
    protein_g: float
    fat_g: float
    carbs_g: float
    fiber_g: float
    rate_kg_week: float
    notes: list[str] = field(default_factory=list)


def goal_rate_kg_week(
    goal: Goal,
    weight_kg: float,
    *,
    rate_kg_week: float | None,
    target_weight_kg: float | None,
    target_date: date | None,
    today: date,
) -> tuple[float, list[str]]:
    """Ritmo de cambio de peso (negativo = perder) y avisos de seguridad."""
    notes: list[str] = []
    if goal == "mantener":
        return 0.0, notes
    if goal == "ganar":
        return abs(rate_kg_week or DEFAULT_GAIN_KG_WEEK), notes
    if goal == "perder":
        rate = abs(rate_kg_week or DEFAULT_LOSS_KG_WEEK)
    else:  # corte hacia una categoría
        rate = weight_kg * DEFAULT_CUT_PCT_WEEK
        if target_weight_kg is not None and target_date is not None and target_date > today:
            weeks = max((target_date - today).days / 7, 0.5)
            rate = max(0.0, (weight_kg - target_weight_kg) / weeks)
        elif target_weight_kg is not None and target_weight_kg >= weight_kg:
            notes.append("Ya estás en tu peso objetivo: mantenimiento.")
            return 0.0, notes
    max_rate = weight_kg * MAX_SAFE_PCT_WEEK
    if rate > max_rate:
        notes.append(
            f"El ritmo necesario ({rate:.2f} kg/semana) supera el 1 % del peso por semana: "
            f"se limita a {max_rate:.2f}. Valora ampliar la fecha o la categoría."
        )
        rate = max_rate
    return -round(rate, 3), notes


def daily_target(
    *,
    weight_kg: float,
    height_cm: float,
    age: int,
    sex: Sex,
    activity_factor: float,
    training_kcal: float,
    goal: Goal,
    protein_g_per_kg: float,
    rate_kg_week: float | None = None,
    target_weight_kg: float | None = None,
    target_date: date | None = None,
    today: date,
) -> DailyTarget:
    bmr = bmr_mifflin(weight_kg, height_cm, age, sex)
    daily_activity = bmr * activity_factor
    maintenance = daily_activity + training_kcal
    rate, notes = goal_rate_kg_week(
        goal,
        weight_kg,
        rate_kg_week=rate_kg_week,
        target_weight_kg=target_weight_kg,
        target_date=target_date,
        today=today,
    )
    adjustment = rate * KCAL_PER_KG_FAT / 7
    if adjustment < -maintenance * MAX_DEFICIT_SHARE:
        adjustment = -maintenance * MAX_DEFICIT_SHARE
        notes.append("Déficit limitado al 25 % del mantenimiento.")
    target = maintenance + adjustment
    if target < bmr:
        target = bmr
        notes.append("El objetivo no baja de tu metabolismo basal.")

    protein = protein_g_per_kg * weight_kg
    fat = max(FAT_MIN_G_PER_KG * weight_kg, FAT_MIN_SHARE * target / 9)
    carbs = max(0.0, (target - protein * 4 - fat * 9) / 4)
    return DailyTarget(
        bmr=round(bmr),
        daily_activity_kcal=round(daily_activity),
        training_kcal=round(training_kcal),
        maintenance_kcal=round(maintenance),
        adjustment_kcal=round(adjustment),
        target_kcal=round(target),
        protein_g=round(protein),
        fat_g=round(fat),
        carbs_g=round(carbs),
        fiber_g=round(target / 1000 * FIBER_G_PER_1000_KCAL),
        rate_kg_week=rate,
        notes=notes,
    )


@dataclass(frozen=True)
class WeightTrend:
    latest_kg: float | None
    average_7d_kg: float | None
    change_week_kg: float | None  # media de los últimos 7 días frente a los 7 anteriores


def weight_trend(points: Sequence[tuple[date, float]], today: date) -> WeightTrend:
    """Media móvil de 7 días: suaviza las oscilaciones diarias de agua y glucógeno."""
    ordered = sorted(points)
    if not ordered:
        return WeightTrend(None, None, None)
    recent = [w for d, w in ordered if 0 <= (today - d).days < 7]
    previous = [w for d, w in ordered if 7 <= (today - d).days < 14]
    avg = round(sum(recent) / len(recent), 2) if recent else None
    prev = sum(previous) / len(previous) if previous else None
    change = round(avg - prev, 2) if avg is not None and prev is not None else None
    return WeightTrend(ordered[-1][1], avg, change)
