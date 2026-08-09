"""Estimación determinista de energía (MET) y necesidades calóricas.

Fuentes: Compendium of Physical Activities (ACE/NCBI), Mifflin-St Jeor (1990),
factores PAL FAO/WHO. Todas las cifras son ESTIMACIONES (±10–15%): la tendencia
importa más que el valor absoluto.
"""

# MET por disciplina (compendio, valores representativos).
MET_BY_DISCIPLINE: dict[str, float] = {
    "boxing": 7.8,  # clase/sparring moderado
    "running": 8.2,  # ~8 km/h
    "cycling": 7.1,  # ~20 km/h
    "swimming": 6.0,  # nado recreativo
    "gym": 5.0,  # fuerza general 8-15 reps
    "other": 4.0,
}

# Factor de actividad (PAL) para el TDEE.
PAL_BY_ACTIVITY: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "very_active": 1.725,
    "athlete": 1.9,
}

# Ajuste diario según objetivo.
KCAL_ADJUST_BY_GOAL: dict[str, int] = {
    "loss": -500,
    "maintenance": 0,
    "performance": 300,
}

KG_PER_MONTH_LOSS = 0.5  # referencia: déficit 500 kcal/día ≈ 0.5 kg/semana


def kcal_burned(met: float, weight_kg: float, duration_minutes: float) -> float:
    """Calorías quemadas: MET × peso × horas."""
    return met * weight_kg * (duration_minutes / 60)


def met_for_discipline(discipline: str) -> float:
    return MET_BY_DISCIPLINE.get(discipline, MET_BY_DISCIPLINE["other"])


def bmr_mifflin(weight_kg: float, height_cm: float, age: int, is_male: bool) -> float:
    """Tasa metabólica basal (Mifflin-St Jeor)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if is_male else base - 161


def tdee(bmr: float, activity: str) -> float:
    """Gasto energético total diario."""
    factor = PAL_BY_ACTIVITY.get(activity, PAL_BY_ACTIVITY["moderate"])
    return bmr * factor


def target_kcal(tdee_value: float, goal: str | None) -> float:
    """Calorías objetivo diarias según el objetivo del usuario."""
    return tdee_value + KCAL_ADJUST_BY_GOAL.get(goal or "maintenance", 0)
