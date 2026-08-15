import type { Slug } from "react-muscle-highlighter";

/**
 * Traducción de los nombres de grupo muscular del dominio
 * (muscleMap del catálogo y muscleLoads de disciplinas) a los
 * `Slug` que acepta `react-muscle-highlighter`.
 *
 * Decisiones de mapeo sin correspondencia 1:1 en la librería:
 * - "core": no existe slug "core"; se usa "abs" (abdominales), el más cercano.
 * - "back": la librería divide la espalda en "upper-back", "lower-back" y
 *   "trapezius"; "back" es el rollup genérico del sistema -> "upper-back".
 * - "abductors": sin slug equivalente -> intencionadamente sin mapear
 *   (no se pinta; el render lo ignora sin romper).
 */
export const MUSCLE_SLUG_MAP: Partial<Record<string, Slug>> = {
  quadriceps: "quadriceps",
  hamstrings: "hamstring",
  glutes: "gluteal",
  calves: "calves",
  core: "abs",
  back: "upper-back",
  chest: "chest",
  shoulders: "deltoids",
  biceps: "biceps",
  triceps: "triceps",
  forearms: "forearm",
  neck: "neck",
  lats: "upper-back",
  traps: "trapezius",
  middle_back: "upper-back",
  lower_back: "lower-back",
  abdominals: "abs",
  upper_abs: "abs",
  lower_abs: "abs",
  obliques: "obliques",
  adductors: "adductors",
};

export function mapMuscleGroupToSlug(muscleGroup: string): Slug | null {
  return MUSCLE_SLUG_MAP[muscleGroup] ?? null;
}
