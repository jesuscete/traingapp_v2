import { translateMuscleGroup, translateZone } from "@/lib/labels";
import type {
  CatalogExercise,
  DayType,
  Discipline,
  MuscleImpact,
  RoutineReviewItem,
} from "@/lib/types";

const MUSCLE_ZONE: Record<string, string> = {
  quadriceps: "legs",
  hamstrings: "legs",
  glutes: "legs",
  calves: "legs",
  core: "core",
  back: "back",
  chest: "chest",
  shoulders: "shoulders",
  biceps: "arms",
  triceps: "arms",
  forearms: "arms",
  neck: "neck",
  lats: "back",
  traps: "back",
  middle_back: "back",
  lower_back: "back",
  abdominals: "core",
  upper_abs: "core",
  lower_abs: "core",
  obliques: "core",
  adductors: "legs",
  abductors: "legs",
};

export function zoneOfGroup(group: string): string {
  return MUSCLE_ZONE[group] ?? "other";
}

export type ReviewDay = {
  dayOfWeek: number;
  dayType: DayType;
  label?: string | null;
  disciplineId?: string | null;
  targetDurationMin?: number | string | null;
  exercises?: {
    exerciseId?: string | null;
    name?: string | null;
    sets?: { targetRepsMin?: number | null }[];
  }[];
};

export type ReviewZone = {
  zone: string;
  label: string;
  value: number;
};

export type ReviewWarning = {
  kind: "overload" | "underload";
  muscleGroup: string;
  label: string;
};

export type ZoneTotals = {
  byGroup: Record<string, number>;
  byZone: Record<string, number>;
};

export const OVERLOAD_RATIO_THRESHOLD = 1.4;

const UNDERLOAD_CANDIDATES = [
  "quadriceps",
  "hamstrings",
  "glutes",
  "back",
  "chest",
  "shoulders",
  "biceps",
  "triceps",
  "core",
];

const DAY_LABELS = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
];

function norm(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function round3(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function resolveWeights(
  exercise: NonNullable<ReviewDay["exercises"]>[number],
  byId: Map<string, CatalogExercise>,
  byName: Map<string, CatalogExercise>,
): Record<string, number> {
  const byIdMatch = exercise.exerciseId
    ? byId.get(exercise.exerciseId)
    : undefined;
  const byNameMatch =
    !byIdMatch && exercise.name
      ? byName.get(norm(exercise.name))
      : undefined;
  return byIdMatch?.muscleMap ?? byNameMatch?.muscleMap ?? {};
}

function indexes(
  catalog: CatalogExercise[],
  disciplines: Discipline[],
): {
  byId: Map<string, CatalogExercise>;
  byName: Map<string, CatalogExercise>;
  disciplineById: Map<string, Discipline>;
} {
  return {
    byId: new Map(catalog.map((item) => [item.id, item])),
    byName: new Map(catalog.map((item) => [item.normalizedName, item])),
    disciplineById: new Map(disciplines.map((item) => [item.id, item])),
  };
}

export function computeZoneTotals(
  days: ReviewDay[],
  catalog: CatalogExercise[],
  disciplines: Discipline[],
): ZoneTotals {
  const { byId, byName, disciplineById } = indexes(catalog, disciplines);
  const byGroup: Record<string, number> = {};
  const byZone: Record<string, number> = {};
  const add = (group: string, amount: number) => {
    if (amount <= 0) return;
    byGroup[group] = (byGroup[group] ?? 0) + amount;
    const zone = zoneOfGroup(group);
    byZone[zone] = (byZone[zone] ?? 0) + amount;
  };

  for (const day of days) {
    if (day.dayType === "deporte") {
      const discipline = day.disciplineId
        ? disciplineById.get(day.disciplineId)
        : undefined;
      if (!discipline) continue;
      const duration = Number(day.targetDurationMin) || 45;
      for (const { muscleGroup, load } of discipline.muscleLoads) {
        add(muscleGroup, load * duration);
      }
    } else if (day.dayType === "gimnasio") {
      for (const exercise of day.exercises ?? []) {
        const weights = resolveWeights(exercise, byId, byName);
        if (Object.keys(weights).length === 0) continue;
        const reps = (exercise.sets ?? []).reduce(
          (acc, workoutSet) => acc + (workoutSet.targetRepsMin ?? 0),
          0,
        );
        const volume = reps > 0 ? reps : 1;
        for (const [group, weight] of Object.entries(weights)) {
          add(group, weight * volume);
        }
      }
    }
  }

  return { byGroup, byZone };
}

export function buildZoneReviews(totals: ZoneTotals): ReviewZone[] {
  const entries = Object.entries(totals.byZone).filter(([, value]) => value > 0);
  if (entries.length === 0) return [];
  const max = Math.max(...entries.map(([, value]) => value));
  return entries
    .map(([zone, value]) => ({
      zone,
      label: translateZone(zone),
      value: round3(value / max),
    }))
    .sort((a, b) => b.value - a.value);
}

export function detectImbalances(totals: ZoneTotals): ReviewWarning[] {
  const groups = Object.keys(totals.byGroup).filter(
    (group) => totals.byGroup[group] > 0,
  );
  const warnings: ReviewWarning[] = [];
  if (groups.length === 0) return warnings;

  const values = groups.map((group) => totals.byGroup[group]);
  const mean = values.reduce((acc, value) => acc + value, 0) / values.length;

  for (const group of groups) {
    if (totals.byGroup[group] > mean * OVERLOAD_RATIO_THRESHOLD) {
      warnings.push({
        kind: "overload",
        muscleGroup: group,
        label: `Mucha carga en ${translateMuscleGroup(group)}`,
      });
    }
  }
  warnings.sort(
    (a, b) => totals.byGroup[b.muscleGroup] - totals.byGroup[a.muscleGroup],
  );

  const worked = new Set(groups);
  for (const group of UNDERLOAD_CANDIDATES) {
    if (!worked.has(group)) {
      warnings.push({
        kind: "underload",
        muscleGroup: group,
        label: `Apenas trabajas ${translateMuscleGroup(group)}`,
      });
    }
  }

  return warnings;
}

export function computeMuscleImpacts(
  days: ReviewDay[],
  catalog: CatalogExercise[],
  disciplines: Discipline[],
): MuscleImpact[] {
  const totals = computeZoneTotals(days, catalog, disciplines);
  const groups = Object.keys(totals.byGroup).filter(
    (group) => totals.byGroup[group] > 0,
  );
  if (groups.length === 0) return [];
  const maxTotal = Math.max(...groups.map((group) => totals.byGroup[group]));
  return groups
    .map((group) => ({
      muscleGroup: group,
      activation: round3(totals.byGroup[group] / maxTotal),
      zone: zoneOfGroup(group),
    }))
    .sort((a, b) => b.activation - a.activation);
}

export function buildReviewItems(
  days: ReviewDay[],
  catalog: CatalogExercise[],
  disciplines: Discipline[],
): RoutineReviewItem[] {
  const { byId, byName, disciplineById } = indexes(catalog, disciplines);
  const items: RoutineReviewItem[] = [];

  for (const day of days) {
    const dayLabel = DAY_LABELS[day.dayOfWeek - 1] ?? dayLabelOf(day);
    if (day.dayType === "gimnasio") {
      for (const exercise of day.exercises ?? []) {
        const weights = resolveWeights(exercise, byId, byName);
        if (Object.keys(weights).length === 0) continue;
        const groups = Object.entries(weights)
          .sort((a, b) => b[1] - a[1])
          .map(([group]) => translateMuscleGroup(group));
        const reps = (exercise.sets ?? [])
          .map((workoutSet) => workoutSet.targetRepsMin)
          .filter((value): value is number => value != null);
        items.push({
          diaSemana: dayLabel,
          tipo: "gimnasio",
          nombre: exercise.name || dayLabel,
          gruposMusculares: groups,
          series: (exercise.sets ?? []).length,
          repeticiones: reps.length
            ? Math.round(reps.reduce((acc, value) => acc + value, 0) / reps.length)
            : null,
          duracionMin: null,
        });
      }
    } else if (day.dayType === "deporte") {
      const discipline = day.disciplineId
        ? disciplineById.get(day.disciplineId)
        : undefined;
      const duration = Number(day.targetDurationMin);
      items.push({
        diaSemana: dayLabel,
        tipo: "deporte",
        nombre:
          discipline?.name ?? (day.label ? String(day.label) : dayLabel),
        gruposMusculares: discipline
          ? discipline.muscleLoads.map((item) =>
              translateMuscleGroup(item.muscleGroup),
            )
          : [],
        series: 0,
        repeticiones: null,
        duracionMin: Number.isFinite(duration) && duration > 0 ? duration : null,
      });
    }
  }

  return items;
}

function dayLabelOf(day: ReviewDay): string {
  return typeof day.label === "string" && day.label.trim() ? day.label : `Día ${day.dayOfWeek}`;
}