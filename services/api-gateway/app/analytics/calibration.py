"""Calibracion del modelo de fatiga con DOMS reportado (fatigue-spec 7.3, ADR-015).

Regla de gradiente simple por dia, acotada:
  - delta_g = (DOMS_g - F_g/10) / 10   (ambos en escala 0-10)
  - N_g' = clamp(N_g * (1 + ng_delta), 0.05, 1.0)  con ng_delta acumulado
  - tau2' = tau2 * tau2_factor           (mas dolor -> recuperacion mas lenta)

Validacion (spec 7.5): correlacion de Pearson entre fatiga predicha (dia D-1)
y DOMS reportado (dia D); el nivel de confianza depende del numero de muestras.
"""

import math

from app.analytics.fatigue import MUSCLE_GROUPS

# Parametros del gradiente (acotados por dia).
NG_DELTA_LR = 0.15  # tasa de aprendizaje por dia
NG_DELTA_MAX = 0.40  # cota del ajuste acumulado de N_g
STEP_MAX = 0.15  # cota del gradiente aplicado en un solo paso
TAU2_FACTOR_MIN = 0.85
TAU2_FACTOR_MAX = 1.30
MIN_SAMPLES_MEDIUM = 5
MIN_SAMPLES_HIGH = 10


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def gradient_step(
    predicted: dict[str, float], reported: dict[str, float]
) -> dict[str, float]:
    """Paso de gradiente por grupo: positivo si se reporta mas dolor del predicho."""
    step: dict[str, float] = {}
    for group in MUSCLE_GROUPS:
        pain = reported.get(group, 0)
        pred = predicted.get(group, 0.0) / 10.0  # F (0-100) -> escala 0-10
        step[group] = round(clamp((pain - pred) / 10.0, -STEP_MAX, STEP_MAX), 4)
    return step


def apply_gradient(
    ng_delta: dict[str, float], step: dict[str, float], lr: float = NG_DELTA_LR
) -> dict[str, float]:
    """Acumula el gradiente acotado en la correccion `ng_delta` de cada grupo."""
    return {
        g: round(
            clamp(ng_delta.get(g, 0.0) + lr * step.get(g, 0.0), -NG_DELTA_MAX, NG_DELTA_MAX),
            4,
        )
        for g in MUSCLE_GROUPS
    }


def ng_factor(ng_delta: float) -> float:
    """Factor multiplicativo aplicado a `N_g` del catalogo (>= 0.05)."""
    return round(clamp(1.0 + ng_delta, 0.05, 1.0 + NG_DELTA_MAX), 3)


def tau2_factor_from(ng_delta: dict[str, float]) -> dict[str, float]:
    """Multiplicador de tau2 por grupo derivado del gradiente acumulado."""
    return {
        g: round(clamp(1.0 + ng_delta.get(g, 0.0), TAU2_FACTOR_MIN, TAU2_FACTOR_MAX), 3)
        for g in MUSCLE_GROUPS
    }


def pearson(pairs: list[tuple[float, float]]) -> float | None:
    """Correlacion de Pearson entre fatiga predicha y DOMS reportado."""
    n = len(pairs)
    if n < 2:
        return None
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in pairs)
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0 or var_y <= 0:
        return None
    r = cov / math.sqrt(var_x * var_y)
    return round(clamp(r, -1.0, 1.0), 3)


def confidence_level(sample_count: int) -> str:
    """Nivel de confianza del calibrador segun el numero de muestras (spec 7.5)."""
    if sample_count >= MIN_SAMPLES_HIGH:
        return "alta"
    if sample_count >= MIN_SAMPLES_MEDIUM:
        return "media"
    return "baja"
