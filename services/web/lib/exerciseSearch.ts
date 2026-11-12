import type { CatalogExercise } from "@/lib/types";

export const PRIMARY_THRESHOLD = 0.5;

export function normalizeText(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

export function exerciseDisplayName(ex: CatalogExercise): string {
  return ex.details?.nameEs?.trim() || ex.name;
}

export function exerciseInstructions(ex: CatalogExercise): string[] {
  const es = ex.details?.instructionsEs;
  if (es && es.length > 0) return es;
  return ex.details?.instructions ?? [];
}

export function primaryMuscles(ex: CatalogExercise): string[] {
  return Object.entries(ex.muscleMap)
    .filter(([, value]) => value >= PRIMARY_THRESHOLD)
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);
}

export function secondaryMuscles(ex: CatalogExercise): string[] {
  return Object.entries(ex.muscleMap)
    .filter(([, value]) => value > 0 && value < PRIMARY_THRESHOLD)
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);
}

/** Alias en inglés de los ejercicios canónicos (nombre solo en español) para buscar "bench press". */
const ENGLISH_ALIASES: Record<string, string> = {
  "press banca": "bench press barbell",
  "press inclinado": "incline bench press",
  "press declinado": "decline bench press",
  aperturas: "chest fly flyes",
  "fondos en paralelas": "dips parallel bars",
  "press con mancuernas": "dumbbell bench press",
  "press militar": "overhead press military press shoulder press",
  "elevaciones laterales": "lateral raise",
  "elevaciones frontales": "front raise",
  "elevaciones posteriores": "rear delt raise reverse fly",
  "remo con barra": "barbell row bent over row",
  "remo mancuerna": "dumbbell row one arm row",
  "remo sentado": "seated cable row",
  dominadas: "pull up pullup chin up",
  "jalon al pecho": "lat pulldown",
  "face pull": "face pull",
  "peso muerto": "deadlift",
  "peso muerto rumano": "romanian deadlift rdl",
  sentadilla: "squat back squat",
  "sentadilla frontal": "front squat",
  prensa: "leg press",
  zancadas: "lunges lunge",
  "extension de cuadriceps": "leg extension",
  "curl femoral": "leg curl hamstring curl",
  "hip thrust": "hip thrust glute bridge",
  gemelos: "calf raise calves",
  "elevacion de talones": "calf raise",
  "curl biceps": "biceps curl bicep curl",
  "curl martillo": "hammer curl",
  "press frances": "skull crusher lying triceps extension",
  "push down": "triceps pushdown",
  "extensiones de triceps": "triceps extension",
  plancha: "plank",
  crunches: "crunch abs",
  "russian twist": "russian twist",
  "elevacion de piernas": "leg raise",
  "press empujadora": "push press",
  "landmine press": "landmine press",
  "cargada de potencia": "power clean",
  "balanceo con kettlebell": "kettlebell swing",
  "saltos al cajon": "box jump",
  "saltos verticales": "vertical jump",
  "lanzamiento de balon medicinal": "medicine ball throw slam",
  sprints: "sprint",
};

export function searchText(ex: CatalogExercise): string {
  const display = exerciseDisplayName(ex);
  const alias = ENGLISH_ALIASES[normalizeText(ex.name)] ?? "";
  return normalizeText(`${display} ${ex.name} ${alias}`);
}

export type IndexedExercise = {
  ex: CatalogExercise;
  haystack: string;
  primary: string[];
  equipment: string | null;
  category: string | null;
};

export function indexExercises(list: CatalogExercise[]): IndexedExercise[] {
  return list.map((ex) => ({
    ex,
    haystack: searchText(ex),
    primary: primaryMuscles(ex),
    equipment: ex.details?.equipment?.trim() || null,
    category: ex.details?.category?.trim() || null,
  }));
}

export type ExerciseFilters = {
  query: string;
  muscle: string | null;
  equipment: string | null;
  category: string | null;
  favoritesOnly: boolean;
  customOnly: boolean;
};

export const EMPTY_FILTERS: ExerciseFilters = {
  query: "",
  muscle: null,
  equipment: null,
  category: null,
  favoritesOnly: false,
  customOnly: false,
};

export function filterExercises(
  index: IndexedExercise[],
  filters: ExerciseFilters,
): CatalogExercise[] {
  const tokens = normalizeText(filters.query).split(" ").filter(Boolean);
  const out: { ex: CatalogExercise; score: number }[] = [];
  for (const item of index) {
    if (filters.favoritesOnly && !item.ex.isFavorite) continue;
    if (filters.customOnly && !item.ex.isCustom) continue;
    if (filters.muscle && !item.primary.includes(filters.muscle)) continue;
    if (filters.equipment && item.equipment !== filters.equipment) continue;
    if (filters.category && item.category !== filters.category) continue;
    let score = 0;
    if (tokens.length > 0) {
      if (!tokens.every((token) => item.haystack.includes(token))) continue;
      if (item.haystack.startsWith(tokens[0])) score = -1;
    }
    out.push({ ex: item.ex, score });
  }
  out.sort(
    (a, b) =>
      a.score - b.score ||
      Number(b.ex.isFavorite) - Number(a.ex.isFavorite) ||
      exerciseDisplayName(a.ex).localeCompare(exerciseDisplayName(b.ex), "es"),
  );
  return out.map((item) => item.ex);
}

export function distinctValues(
  index: IndexedExercise[],
  pick: (item: IndexedExercise) => string | null,
): string[] {
  const set = new Set<string>();
  for (const item of index) {
    const value = pick(item);
    if (value) set.add(value);
  }
  return [...set].sort((a, b) => a.localeCompare(b, "es"));
}
