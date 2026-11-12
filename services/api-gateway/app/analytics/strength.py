"""1RM estimado: fórmula ÚNICA para toda la app (M4.1).

Se usa la tabla RPE -> %1RM de RTS (Tuchscherer), estándar en entrenamiento de fuerza:
cada medio punto de RPE por debajo de 10 equivale a media repetición más en reserva.
Por eso la tabla completa cabe en una secuencia indexada por
`2·(reps-1) + 2·(10-RPE)`.

- Con RPE (6-10) de la serie: %1RM según reps y RPE.
- Sin RPE: se asume RPE 10 (serie a fallo). Es la estimación conservadora y en esa
  columna coincide prácticamente con Epley/Brzycki (p. ej. 5 reps -> 86,3 %).
- Fuera de 1-12 reps no se estima: la predicción deja de ser fiable.

El frontend tiene una copia exacta en `services/web/lib/strength.ts` y los mismos casos
de prueba (`tests/test_strength.py`). Mantener ambas sincronizadas.
"""

MIN_REPS = 1
MAX_REPS = 12
MIN_RPE = 6.0
MAX_RPE = 10.0

# %1RM para (reps=1, RPE=10), (reps=1, RPE=9.5)=(reps=1.5, RPE=10), ...
RPE_CHART: tuple[float, ...] = (
    100.0,
    97.8,
    95.5,
    93.9,
    92.2,
    90.7,
    89.2,
    87.8,
    86.3,
    85.0,
    83.7,
    82.4,
    81.1,
    79.9,
    78.6,
    77.4,
    76.2,
    75.1,
    73.9,
    72.3,
    70.7,
    69.4,
    68.0,
    66.7,
    65.3,
    64.0,
    62.6,
    61.3,
    59.9,
    58.6,
    57.3,
)


def percent_of_1rm(reps: int, rpe: float | None = None) -> float | None:
    """Porcentaje del 1RM que supone una serie de `reps` a un `rpe` dado."""
    if reps < MIN_REPS or reps > MAX_REPS:
        return None
    effective_rpe = MAX_RPE if rpe is None else min(MAX_RPE, max(MIN_RPE, rpe))
    index = 2 * (reps - 1) + round(2 * (MAX_RPE - effective_rpe))
    return RPE_CHART[index]


def estimated_1rm(
    weight_kg: float | None, reps: int | None, rpe: float | None = None
) -> float | None:
    """1RM estimado (kg, 1 decimal) o None si no hay datos válidos."""
    if weight_kg is None or reps is None or weight_kg <= 0:
        return None
    pct = percent_of_1rm(reps, rpe)
    if pct is None:
        return None
    return round(weight_kg * 100 / pct, 1)
