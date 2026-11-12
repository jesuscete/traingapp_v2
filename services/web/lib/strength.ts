/**
 * 1RM estimado: copia EXACTA de services/api-gateway/app/analytics/strength.py.
 * Tabla RPE -> %1RM (RTS/Tuchscherer); sin RPE se asume RPE 10; solo 1-12 reps.
 * Vectores de prueba compartidos: tests/test_strength.py (mantener sincronizados).
 */

const MIN_REPS = 1;
const MAX_REPS = 12;
const MIN_RPE = 6;
const MAX_RPE = 10;

const RPE_CHART: readonly number[] = [
  100.0, 97.8, 95.5, 93.9, 92.2, 90.7, 89.2, 87.8, 86.3, 85.0, 83.7, 82.4, 81.1, 79.9, 78.6,
  77.4, 76.2, 75.1, 73.9, 72.3, 70.7, 69.4, 68.0, 66.7, 65.3, 64.0, 62.6, 61.3, 59.9, 58.6,
  57.3,
];

export function percentOf1rm(reps: number, rpe?: number | null): number | null {
  if (!Number.isInteger(reps) || reps < MIN_REPS || reps > MAX_REPS) return null;
  const effective = rpe == null ? MAX_RPE : Math.min(MAX_RPE, Math.max(MIN_RPE, rpe));
  return RPE_CHART[2 * (reps - 1) + Math.round(2 * (MAX_RPE - effective))];
}

export function estimated1rm(
  weightKg: number | null | undefined,
  reps: number | null | undefined,
  rpe?: number | null,
): number | null {
  if (weightKg == null || reps == null || weightKg <= 0) return null;
  const pct = percentOf1rm(reps, rpe);
  if (pct == null) return null;
  return Math.round((weightKg * 1000) / pct) / 10;
}
