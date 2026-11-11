import { uid } from "@/lib/workout/ops";
import type {
  ClimbingStyle,
  CombatBlock,
  CombatBlockType,
  SessionMetrics,
} from "@/lib/types";

export type MetricsKind = SessionMetrics["kind"];

export const ENDURANCE_DISCIPLINES = ["running", "cycling", "swimming", "ski_snowboard"];

export function metricsKindFor(discipline: string): MetricsKind {
  if (discipline === "boxing" || discipline === "martial_arts") return "combat";
  if (ENDURANCE_DISCIPLINES.includes(discipline)) return "endurance";
  if (discipline === "climbing") return "climbing";
  return "generic";
}

/** Disciplinas elegibles para /registrar (gimnasio se registra en /entrenar). */
export const LOGGABLE_DISCIPLINES: string[] = [
  "boxing",
  "martial_arts",
  "running",
  "cycling",
  "swimming",
  "climbing",
  "calisthenics",
  "football",
  "basketball",
  "volleyball",
  "tennis",
  "badminton",
  "table_tennis",
  "handball",
  "rugby",
  "hockey",
  "baseball",
  "cricket",
  "ski_snowboard",
  "golf",
  "other",
];

export const BLOCK_TYPE_LABELS: Record<CombatBlockType, string> = {
  saco: "Saco",
  sparring: "Sparring",
  manoplas: "Manoplas",
  comba: "Comba",
  sombra: "Sombra",
  tecnica: "Técnica",
  fisico: "Físico",
};

export const BLOCK_TYPES = Object.keys(BLOCK_TYPE_LABELS) as CombatBlockType[];

export const CLIMBING_STYLE_LABELS: Record<ClimbingStyle, string> = {
  boulder: "Boulder",
  via: "Vía",
  autobelay: "Autoseguro",
  exterior: "Exterior",
};

export const CLIMBING_STYLES = Object.keys(CLIMBING_STYLE_LABELS) as ClimbingStyle[];

export const ROUTE_GRADES = ["5", "6a", "6a+", "6b", "6b+", "6c", "7a"];
export const BOULDER_GRADES = ["V0", "V1", "V2", "V3", "V4", "V5", "V6", "V7"];

/* ---------- Estado de formulario ---------- */

export type BlockForm = {
  id: string;
  type: CombatBlockType;
  mode: "rounds" | "minutes";
  rounds: string;
  roundTime: string;
  minutes: string;
  strikes: string;
};

export type RouteForm = {
  id: string;
  grade: string;
  attempts: string;
  sent: boolean;
};

export type MetricsForm = {
  blocks: BlockForm[];
  distanceKm: string;
  avgHr: string;
  maxHr: string;
  elevation: string;
  style: ClimbingStyle;
  routes: RouteForm[];
  notes: string;
};

export function newBlock(): BlockForm {
  return {
    id: uid(),
    type: "saco",
    mode: "rounds",
    rounds: "5",
    roundTime: "3:00",
    minutes: "",
    strikes: "",
  };
}

export function newRoute(grade = "", sent = true): RouteForm {
  return { id: uid(), grade, attempts: "1", sent };
}

export function emptyMetricsForm(): MetricsForm {
  return {
    blocks: [newBlock()],
    distanceKm: "",
    avgHr: "",
    maxHr: "",
    elevation: "",
    style: "boulder",
    routes: [],
    notes: "",
  };
}

export function formatRoundTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** Acepta "3:00", "2:30" o "3" (minutos). Devuelve segundos o null. */
export function parseRoundTime(value: string): number | null {
  const text = value.trim().replace(",", ".");
  if (!text) return null;
  const match = /^(\d{1,3}):([0-5]?\d)$/.exec(text);
  if (match) return Number(match[1]) * 60 + Number(match[2]);
  const minutes = Number(text);
  if (Number.isFinite(minutes) && minutes > 0) return Math.round(minutes * 60);
  return null;
}

function num(value: string): number | null {
  const text = value.trim().replace(",", ".");
  if (!text) return null;
  const n = Number(text);
  return Number.isFinite(n) ? n : null;
}

export function metricsToForm(metrics: SessionMetrics | null | undefined): MetricsForm {
  const form = emptyMetricsForm();
  if (!metrics) return form;
  switch (metrics.kind) {
    case "combat":
      form.blocks = metrics.blocks.map((b) => ({
        id: uid(),
        type: b.type,
        mode: b.rounds != null ? "rounds" : "minutes",
        rounds: b.rounds != null ? String(b.rounds) : "",
        roundTime: formatRoundTime(b.roundSeconds ?? 180),
        minutes: b.minutes != null ? String(b.minutes) : "",
        strikes: b.strikes != null ? String(b.strikes) : "",
      }));
      break;
    case "endurance":
      form.distanceKm =
        metrics.distanceMeters != null ? String(metrics.distanceMeters / 1000) : "";
      form.avgHr = metrics.avgHeartRate != null ? String(metrics.avgHeartRate) : "";
      form.maxHr = metrics.maxHeartRate != null ? String(metrics.maxHeartRate) : "";
      form.elevation = metrics.elevationGainM != null ? String(metrics.elevationGainM) : "";
      break;
    case "climbing":
      form.style = metrics.style;
      form.routes = metrics.routes.map((r) => ({
        id: uid(),
        grade: r.grade,
        attempts: r.attempts != null ? String(r.attempts) : "",
        sent: r.sent,
      }));
      break;
    case "generic":
      form.notes = metrics.notes ?? "";
      break;
  }
  return form;
}

export function blockMinutes(block: BlockForm): number {
  if (block.mode === "minutes") return num(block.minutes) ?? 0;
  const rounds = num(block.rounds) ?? 0;
  const seconds = parseRoundTime(block.roundTime) ?? 0;
  return (rounds * seconds) / 60;
}

export function totalCombatMinutes(blocks: BlockForm[]): number {
  return blocks.reduce((total, b) => total + blockMinutes(b), 0);
}

export type MetricsResult = { metrics: SessionMetrics | null; error: string | null };

function intInRange(value: string, min: number, max: number, label: string): [number | null, string | null] {
  if (!value.trim()) return [null, null];
  const n = num(value);
  if (n == null || !Number.isInteger(n) || n < min || n > max) {
    return [null, `${label} debe ser un entero entre ${min} y ${max}.`];
  }
  return [n, null];
}

/** Convierte el formulario en métricas del API validando en cliente. */
export function formToMetrics(kind: MetricsKind, form: MetricsForm): MetricsResult {
  const fail = (error: string): MetricsResult => ({ metrics: null, error });

  if (kind === "combat") {
    if (form.blocks.length === 0) return fail("Añade al menos un bloque.");
    if (form.blocks.length > 20) return fail("Máximo 20 bloques.");
    const blocks: CombatBlock[] = [];
    for (let i = 0; i < form.blocks.length; i += 1) {
      const b = form.blocks[i];
      const tag = `Bloque ${i + 1}`;
      const block: CombatBlock = { type: b.type };
      if (b.mode === "rounds") {
        const [rounds, err] = intInRange(b.rounds, 1, 50, `${tag}: rounds`);
        if (err) return fail(err);
        if (rounds == null) return fail(`${tag}: indica los rounds.`);
        const seconds = parseRoundTime(b.roundTime);
        if (seconds == null || seconds < 10 || seconds > 600) {
          return fail(`${tag}: duración del round entre 0:10 y 10:00.`);
        }
        block.rounds = rounds;
        block.roundSeconds = seconds;
      } else {
        const minutes = num(b.minutes);
        if (minutes == null || minutes <= 0 || minutes > 300) {
          return fail(`${tag}: minutos entre 1 y 300.`);
        }
        block.minutes = minutes;
      }
      if (b.strikes.trim()) {
        const strikes = num(b.strikes);
        if (strikes == null || strikes < 0 || !Number.isInteger(strikes)) {
          return fail(`${tag}: golpes debe ser un entero ≥ 0.`);
        }
        block.strikes = strikes;
      }
      blocks.push(block);
    }
    return { metrics: { kind: "combat", blocks }, error: null };
  }

  if (kind === "endurance") {
    const out: SessionMetrics = { kind: "endurance" };
    if (form.distanceKm.trim()) {
      const km = num(form.distanceKm);
      if (km == null || km <= 0) return fail("Distancia no válida.");
      out.distanceMeters = Math.round(km * 1000);
    }
    const [avg, e1] = intInRange(form.avgHr, 30, 230, "FC media");
    if (e1) return fail(e1);
    const [max, e2] = intInRange(form.maxHr, 30, 240, "FC máxima");
    if (e2) return fail(e2);
    if (avg != null && max != null && avg > max) return fail("La FC media no puede superar la máxima.");
    if (avg != null) out.avgHeartRate = avg;
    if (max != null) out.maxHeartRate = max;
    if (form.elevation.trim()) {
      const el = num(form.elevation);
      if (el == null || el < 0) return fail("Desnivel no válido.");
      out.elevationGainM = el;
    }
    return { metrics: out, error: null };
  }

  if (kind === "climbing") {
    if (form.routes.length > 100) return fail("Máximo 100 vías.");
    const routes = [];
    for (let i = 0; i < form.routes.length; i += 1) {
      const r = form.routes[i];
      const grade = r.grade.trim();
      if (!grade) return fail(`Vía ${i + 1}: indica el grado.`);
      if (grade.length > 12) return fail(`Vía ${i + 1}: grado demasiado largo.`);
      const [attempts, err] = intInRange(r.attempts, 1, 100, `Vía ${i + 1}: intentos`);
      if (err) return fail(err);
      routes.push({ grade, ...(attempts != null ? { attempts } : {}), sent: r.sent });
    }
    return { metrics: { kind: "climbing", style: form.style, routes }, error: null };
  }

  const notes = form.notes.trim();
  if (notes.length > 500) return fail("Las notas admiten hasta 500 caracteres.");
  return { metrics: { kind: "generic", ...(notes ? { notes } : {}) }, error: null };
}

/* ---------- Presentación ---------- */

function trimNumber(n: number, digits = 1): string {
  return String(Number(n.toFixed(digits)));
}

export function formatPaceText(discipline: string, distanceMeters: number | null | undefined, minutes: number | null | undefined): string | null {
  if (!distanceMeters || !minutes || distanceMeters <= 0 || minutes <= 0) return null;
  if (discipline === "running") {
    const secPerKm = (minutes * 60) / (distanceMeters / 1000);
    return `${formatRoundTime(secPerKm)} min/km`;
  }
  if (discipline === "cycling") {
    return `${trimNumber(distanceMeters / 1000 / (minutes / 60))} km/h`;
  }
  if (discipline === "swimming") {
    const secPer100 = (minutes * 60) / (distanceMeters / 100);
    return `${formatRoundTime(secPer100)} min/100 m`;
  }
  return null;
}

export function formatDistance(meters: number): string {
  return meters >= 1000 ? `${trimNumber(meters / 1000, 2)} km` : `${Math.round(meters)} m`;
}

export function combatTotals(blocks: CombatBlock[]): { rounds: number; minutes: number } {
  let rounds = 0;
  let minutes = 0;
  for (const b of blocks) {
    if (b.rounds != null) {
      rounds += b.rounds;
      minutes += (b.rounds * (b.roundSeconds ?? 180)) / 60;
    } else if (b.minutes != null) {
      minutes += b.minutes;
    }
  }
  return { rounds, minutes };
}

export function formatBlock(b: CombatBlock): string {
  const label = BLOCK_TYPE_LABELS[b.type] ?? b.type;
  if (b.rounds != null) return `${label} ${b.rounds}×${formatRoundTime(b.roundSeconds ?? 180)}`;
  return `${label} ${trimNumber(b.minutes ?? 0)} min`;
}

/** Resumen de una línea de las métricas (chat, historial). */
export function summarizeMetrics(metrics: SessionMetrics | null | undefined): string {
  if (!metrics) return "";
  switch (metrics.kind) {
    case "combat":
      return metrics.blocks.map(formatBlock).join(" · ");
    case "endurance": {
      const parts: string[] = [];
      if (metrics.distanceMeters != null) parts.push(formatDistance(metrics.distanceMeters));
      if (metrics.avgHeartRate != null) parts.push(`FC ${metrics.avgHeartRate}`);
      if (metrics.elevationGainM != null) parts.push(`+${Math.round(metrics.elevationGainM)} m`);
      return parts.join(" · ");
    }
    case "climbing": {
      const sent = metrics.routes.filter((r) => r.sent).length;
      const grades = metrics.routes.map((r) => r.grade).join(", ");
      return `${CLIMBING_STYLE_LABELS[metrics.style] ?? metrics.style}: ${sent}/${metrics.routes.length} encadenadas${grades ? ` (${grades})` : ""}`;
    }
    case "generic":
      return metrics.notes ?? "";
  }
}
