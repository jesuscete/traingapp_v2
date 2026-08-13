import { api } from "@/lib/api";
import {
  buildReviewItems,
  buildZoneReviews,
  computeZoneTotals,
  detectImbalances,
  type ReviewDay,
  type ReviewWarning,
  type ReviewZone,
} from "@/lib/routineReview";
import type { CatalogExercise, Discipline, RoutineReview } from "@/lib/types";

export type ReviewSource = "ai" | "local";

export type RoutineReviewResult = {
  source: ReviewSource;
  server: RoutineReview | null;
  radar: ReviewZone[];
  warnings: ReviewWarning[];
};

export async function reviewRoutineDraft(
  token: string,
  routineName: string,
  days: ReviewDay[],
  catalog: CatalogExercise[],
  disciplines: Discipline[],
): Promise<RoutineReviewResult> {
  const totals = computeZoneTotals(days, catalog, disciplines);
  const radar = buildZoneReviews(totals);
  const warnings = detectImbalances(totals);
  const base: RoutineReviewResult = { source: "ai", server: null, radar, warnings };

  if (days.every((day) => day.dayType === "descanso")) return base;

  try {
    const server = await api.reviewRoutine(token, {
      routineName: routineName.trim() || "Rutina",
      days: buildReviewItems(days, catalog, disciplines),
    });
    return { ...base, server };
  } catch {
    return { ...base, source: "local", server: null };
  }
}

export function emptyServerReview(): RoutineReview {
  return { puntosFuertes: [], solapamientos: [], sugerencias: [] };
}