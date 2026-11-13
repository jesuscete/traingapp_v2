/** WODs de CrossFit/HYROX: etiquetas, plantilla HYROX y conversión formulario <-> métricas. */

import { uid } from "@/lib/workout/ops";
import type { HyroxCategory, WodFormat, WodMetrics, WodMovement } from "@/lib/types";

export const WOD_FORMAT_LABELS: Record<WodFormat, string> = {
  for_time: "For Time",
  amrap: "AMRAP",
  emom: "EMOM",
  tabata: "Tabata",
  intervals: "Intervalos",
  strength: "Fuerza / Halterofilia",
  hyrox_sim: "Simulación HYROX",
  hyrox_race: "Carrera HYROX",
  other: "Otro",
};

export const WOD_FORMAT_HELP: Record<WodFormat, string> = {
  for_time: "Terminar el trabajo lo antes posible (rondas fijas, chipper, 21-15-9…).",
  amrap: "Máximas rondas o reps en un tiempo fijo.",
  emom: "Cada minuto haces el trabajo y descansas lo que sobre.",
  tabata: "8 rondas de 20 s de trabajo y 10 s de descanso.",
  intervals: "Bloques de trabajo y descanso fijos.",
  strength: "Series de fuerza o halterofilia: apunta la carga máxima.",
  hyrox_sim: "Entreno con estaciones HYROX (completo o parcial).",
  hyrox_race: "Competición oficial: 8 × (1 km + estación).",
  other: "Cualquier otro formato.",
};

export const HYROX_CATEGORY_LABELS: Record<HyroxCategory, string> = {
  open_men: "Open hombre",
  open_women: "Open mujer",
  pro_men: "Pro hombre",
  pro_women: "Pro mujer",
  doubles: "Dobles",
  relay: "Relevos",
};

/** Qué resultado se apunta según el formato. */
export type ScoreKind = "time" | "rounds" | "reps" | "load";

export function scoreKindFor(format: WodFormat): ScoreKind {
  if (format === "amrap") return "rounds";
  if (format === "emom" || format === "tabata" || format === "intervals") return "reps";
  if (format === "strength") return "load";
  return "time";
}

export function usesTimeCap(format: WodFormat): boolean {
  return format === "for_time" || format === "amrap" || format === "emom" || format === "intervals";
}

export function isHyrox(format: WodFormat): boolean {
  return format === "hyrox_sim" || format === "hyrox_race";
}

/* ---------- HYROX ---------- */

type Station = { name: string; distanceM?: number; reps?: number; weights?: Partial<Record<HyroxCategory, number>> };

/**
 * Estaciones oficiales en orden, pesos de la temporada 2025/26 (el del trineo incluye el
 * trineo; Open hombre = Pro mujer). Contrastados con Red Bull, RoxLyfe y Fitnessvolt.
 * Duda abierta: Fitnessvolt dice que Open mujer bajó a 75 wall balls; otras fuentes
 * mantienen 100. Se deja 100 (editable en el formulario) hasta confirmarlo en el reglamento.
 */
export const HYROX_STATIONS: Station[] = [
  { name: "SkiErg", distanceM: 1000 },
  { name: "Sled Push", distanceM: 50, weights: { open_men: 152, open_women: 102, pro_men: 202, pro_women: 152 } },
  { name: "Sled Pull", distanceM: 50, weights: { open_men: 103, open_women: 78, pro_men: 153, pro_women: 103 } },
  { name: "Burpee Broad Jump", distanceM: 80 },
  { name: "Rowing Machine", distanceM: 1000 },
  { name: "Farmer's Walk", distanceM: 200, weights: { open_men: 24, open_women: 16, pro_men: 32, pro_women: 24 } },
  { name: "Sandbag Lunges", distanceM: 100, weights: { open_men: 20, open_women: 10, pro_men: 30, pro_women: 20 } },
  { name: "Wall Ball", reps: 100, weights: { open_men: 6, open_women: 4, pro_men: 9, pro_women: 6 } },
];

/** Los 16 tramos de una carrera: Run 1, SkiErg, Run 2, Sled Push… */
export function hyroxSplitNames(): string[] {
  return HYROX_STATIONS.flatMap((station, i) => [`Run ${i + 1}`, station.name]);
}

/* ---------- Formulario ---------- */

export type MovementUnit = "reps" | "distance" | "calories";

export type MovementForm = {
  id: string;
  exerciseId: string | null;
  name: string;
  unit: MovementUnit;
  amount: string;
  weight: string;
};

export type SplitForm = { id: string; name: string; time: string };

export type WodForm = {
  format: WodFormat;
  name: string;
  scheme: string;
  timeCap: string;
  time: string;
  capped: boolean;
  rounds: string;
  extraReps: string;
  totalReps: string;
  load: string;
  rx: boolean;
  hyroxCategory: HyroxCategory;
  movements: MovementForm[];
  splits: SplitForm[];
};

export function emptyWodForm(discipline = "crossfit"): WodForm {
  return {
    format: discipline === "hyrox" ? "hyrox_sim" : "for_time",
    name: "",
    scheme: "",
    timeCap: "",
    time: "",
    capped: false,
    rounds: "",
    extraReps: "",
    totalReps: "",
    load: "",
    rx: true,
    hyroxCategory: "open_men",
    movements: [],
    splits: [],
  };
}

export function newMovement(partial: Partial<MovementForm> = {}): MovementForm {
  return { id: uid(), exerciseId: null, name: "", unit: "reps", amount: "", weight: "", ...partial };
}

/** Estaciones HYROX (con pesos de la categoría) y los 16 tramos vacíos. */
export function hyroxTemplate(category: HyroxCategory): Pick<WodForm, "movements" | "splits"> {
  const movements = [
    newMovement({ name: "Run", unit: "distance", amount: "8000" }),
    ...HYROX_STATIONS.map((s) =>
      newMovement({
        name: s.name,
        unit: s.reps ? "reps" : "distance",
        amount: String(s.reps ?? s.distanceM ?? ""),
        weight: s.weights?.[category] != null ? String(s.weights[category]) : "",
      }),
    ),
  ];
  const splits = hyroxSplitNames().map((name) => ({ id: uid(), name, time: "" }));
  return { movements, splits };
}

/** "4:35", "1:02:10" o "275" (segundos) -> segundos. */
export function parseClock(value: string): number | null {
  const text = value.trim();
  if (!text) return null;
  if (/^\d+$/.test(text)) return Number(text);
  const parts = text.split(":").map((p) => Number(p));
  if (parts.some((p) => !Number.isFinite(p) || p < 0) || parts.length > 3) return null;
  return parts.reduce((total, p) => total * 60 + p, 0);
}

export function formatClock(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.round(seconds % 60);
  const mm = h > 0 ? String(m).padStart(2, "0") : String(m);
  return `${h > 0 ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

function num(value: string): number | null {
  if (!value.trim()) return null;
  const n = Number(value.replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

type Result = { metrics: WodMetrics | null; error: string | null };

export function wodFormToMetrics(form: WodForm): Result {
  const fail = (error: string): Result => ({ metrics: null, error });
  const out: WodMetrics = { kind: "wod", format: form.format, rx: form.rx };
  if (form.name.trim()) out.name = form.name.trim().slice(0, 80);
  if (form.scheme.trim()) out.scheme = form.scheme.trim().slice(0, 60);

  if (usesTimeCap(form.format) && form.timeCap.trim()) {
    const cap = num(form.timeCap);
    if (cap == null || cap <= 0 || cap > 360) return fail("Time cap: minutos entre 1 y 360.");
    out.timeCapMinutes = cap;
  }

  const score = scoreKindFor(form.format);
  if (score === "time") {
    if (form.capped) {
      const reps = num(form.totalReps);
      if (reps == null || reps < 0 || !Number.isInteger(reps)) return fail("Indica las reps hechas al llegar al time cap.");
      out.totalReps = reps;
    } else if (form.time.trim()) {
      const seconds = parseClock(form.time);
      if (seconds == null || seconds < 1 || seconds > 6 * 3600) return fail("Tiempo no válido (usa mm:ss).");
      out.timeSeconds = seconds;
    }
  } else if (score === "rounds") {
    const rounds = num(form.rounds);
    const extra = num(form.extraReps);
    if (form.rounds.trim() && (rounds == null || rounds < 0 || !Number.isInteger(rounds))) return fail("Rondas no válidas.");
    if (form.extraReps.trim() && (extra == null || extra < 0 || !Number.isInteger(extra))) return fail("Reps extra no válidas.");
    if (rounds != null) out.rounds = rounds;
    if (extra != null && extra > 0) out.extraReps = extra;
  } else if (score === "reps") {
    const reps = num(form.totalReps);
    if (form.totalReps.trim() && (reps == null || reps < 0 || !Number.isInteger(reps))) return fail("Reps no válidas.");
    if (reps != null) out.totalReps = reps;
  } else {
    const load = num(form.load);
    if (form.load.trim() && (load == null || load <= 0 || load > 500)) return fail("Carga no válida (kg).");
    if (load != null) out.loadKg = load;
  }

  if (isHyrox(form.format)) out.hyroxCategory = form.hyroxCategory;

  const movements: WodMovement[] = [];
  for (let i = 0; i < form.movements.length; i += 1) {
    const m = form.movements[i];
    const name = m.name.trim();
    if (!name) continue;
    const tag = `Movimiento ${i + 1}`;
    const movement: WodMovement = { name: name.slice(0, 120) };
    if (m.exerciseId) movement.exerciseId = m.exerciseId;
    const amount = num(m.amount);
    if (m.amount.trim()) {
      if (amount == null || amount <= 0) return fail(`${tag}: cantidad no válida.`);
      if (m.unit === "reps") movement.reps = Math.round(amount);
      else if (m.unit === "distance") movement.distanceM = amount;
      else movement.calories = Math.round(amount);
    }
    const weight = num(m.weight);
    if (m.weight.trim()) {
      if (weight == null || weight <= 0 || weight > 500) return fail(`${tag}: peso no válido.`);
      movement.weightKg = weight;
    }
    movements.push(movement);
  }
  if (movements.length > 30) return fail("Máximo 30 movimientos.");
  if (movements.length) out.movements = movements;

  const splits = [];
  for (const split of form.splits) {
    if (!split.time.trim()) continue;
    const seconds = parseClock(split.time);
    if (seconds == null || seconds < 1) return fail(`${split.name}: tiempo no válido (mm:ss).`);
    splits.push({ name: split.name.slice(0, 60), seconds });
  }
  if (splits.length) {
    out.splits = splits;
    if (out.timeSeconds == null && !form.capped) out.timeSeconds = splits.reduce((t, s) => t + s.seconds, 0);
  }
  return { metrics: out, error: null };
}

export function wodMetricsToForm(metrics: WodMetrics): WodForm {
  const form = emptyWodForm();
  form.format = metrics.format;
  form.name = metrics.name ?? "";
  form.scheme = metrics.scheme ?? "";
  form.timeCap = metrics.timeCapMinutes != null ? String(metrics.timeCapMinutes) : "";
  form.time = metrics.timeSeconds != null ? formatClock(metrics.timeSeconds) : "";
  form.capped = metrics.timeSeconds == null && metrics.totalReps != null && scoreKindFor(metrics.format) === "time";
  form.rounds = metrics.rounds != null ? String(metrics.rounds) : "";
  form.extraReps = metrics.extraReps != null ? String(metrics.extraReps) : "";
  form.totalReps = metrics.totalReps != null ? String(metrics.totalReps) : "";
  form.load = metrics.loadKg != null ? String(metrics.loadKg) : "";
  form.rx = metrics.rx ?? true;
  form.hyroxCategory = metrics.hyroxCategory ?? "open_men";
  form.movements = (metrics.movements ?? []).map((m) =>
    newMovement({
      exerciseId: m.exerciseId ?? null,
      name: m.name,
      unit: m.distanceM != null ? "distance" : m.calories != null ? "calories" : "reps",
      amount: String(m.distanceM ?? m.calories ?? m.reps ?? ""),
      weight: m.weightKg != null ? String(m.weightKg) : "",
    }),
  );
  form.splits = (metrics.splits ?? []).map((s) => ({ id: uid(), name: s.name, time: formatClock(s.seconds) }));
  return form;
}

/** Resultado legible: "4:35", "18 rondas + 7", "102.5 kg"… */
export function wodScoreText(metrics: WodMetrics): string | null {
  if (metrics.timeSeconds != null) return formatClock(metrics.timeSeconds);
  if (metrics.rounds != null) return `${metrics.rounds} rondas${metrics.extraReps ? ` + ${metrics.extraReps}` : ""}`;
  if (metrics.totalReps != null) return `${metrics.totalReps} reps`;
  if (metrics.loadKg != null) return `${metrics.loadKg} kg`;
  return null;
}

export function movementText(m: WodMovement): string {
  const amount =
    m.distanceM != null
      ? `${m.distanceM >= 1000 ? `${Number((m.distanceM / 1000).toFixed(2))} km` : `${m.distanceM} m`}`
      : m.calories != null
        ? `${m.calories} cal`
        : m.reps != null
          ? `${m.reps}`
          : "";
  return [amount, m.name, m.weightKg != null ? `@ ${m.weightKg} kg` : ""].filter(Boolean).join(" ");
}

export function summarizeWod(metrics: WodMetrics): string {
  const parts = [
    metrics.name || WOD_FORMAT_LABELS[metrics.format],
    metrics.timeCapMinutes != null && metrics.format === "amrap" ? `${metrics.timeCapMinutes} min` : null,
    wodScoreText(metrics),
    metrics.rx === false ? "Scaled" : null,
  ];
  return parts.filter(Boolean).join(" · ");
}
