/** Tendencia de peso y composición corporal y avance hacia el objetivo (sin IA). */

import type { NutritionGoal, WeightPoint } from "@/lib/types";

/** Pesajes mínimos para dibujar la gráfica y hablar de tendencia. */
export const MIN_POINTS = 3;
/** Ventana de la tendencia: lo reciente manda. */
const WINDOW_DAYS = 28;
/** Por debajo de esto (kg/semana) se considera estable. */
const FLAT_KG_WEEK = 0.1;
const FLAT_PCT_WEEK = 0.15;
const DAY_MS = 86_400_000;

export type Direction = "sube" | "baja" | "estable";

export type SeriesTrend = { perWeek: number; direction: Direction };

export type BodyTrend = {
  weight: SeriesTrend | null;
  fat: SeriesTrend | null;
  muscle: SeriesTrend | null;
  /** Frase principal sobre la tendencia. */
  summary: string;
  /** Cómo vas respecto al objetivo (null si no hay objetivo que evaluar). */
  goal: { tone: "ok" | "warn" | "bad"; text: string } | null;
};

function dayNum(iso: string): number {
  const [y, m, d] = iso.split("-").map(Number);
  return Date.UTC(y, m - 1, d) / DAY_MS;
}

/** Pendiente por mínimos cuadrados, en unidades por semana. */
export function slopePerWeek(points: { x: number; y: number }[]): number | null {
  if (points.length < MIN_POINTS) return null;
  const span = points[points.length - 1].x - points[0].x;
  if (span < 5) return null;
  const n = points.length;
  const mx = points.reduce((a, p) => a + p.x, 0) / n;
  const my = points.reduce((a, p) => a + p.y, 0) / n;
  let num = 0;
  let den = 0;
  for (const p of points) {
    num += (p.x - mx) * (p.y - my);
    den += (p.x - mx) ** 2;
  }
  return den === 0 ? null : (num / den) * 7;
}

function trendOf(
  points: WeightPoint[],
  pick: (p: WeightPoint) => number | null | undefined,
  flat: number,
): SeriesTrend | null {
  if (points.length === 0) return null;
  const last = dayNum(points[points.length - 1].measuredOn);
  const xy = points
    .filter((p) => last - dayNum(p.measuredOn) <= WINDOW_DAYS)
    .map((p) => ({ x: dayNum(p.measuredOn), y: pick(p) }))
    .filter((p): p is { x: number; y: number } => p.y != null);
  const perWeek = slopePerWeek(xy);
  if (perWeek === null) return null;
  return { perWeek, direction: Math.abs(perWeek) < flat ? "estable" : perWeek > 0 ? "sube" : "baja" };
}

const fmt = (n: number) => Math.abs(n).toLocaleString("es-ES", { maximumFractionDigits: 1, minimumFractionDigits: 1 });

function addWeeks(fromIso: string, weeks: number): string {
  return new Date((dayNum(fromIso) + weeks * 7) * DAY_MS).toISOString().slice(0, 10);
}

function shortEs(iso: string): string {
  return new Date(dayNum(iso) * DAY_MS).toLocaleDateString("es-ES", { day: "numeric", month: "short", timeZone: "UTC" });
}

function weightSummary(w: SeriesTrend | null, fat: SeriesTrend | null, muscle: SeriesTrend | null): string {
  if (!w) return "Aún hay pocos pesajes recientes para ver una tendencia clara.";
  const base =
    w.direction === "estable"
      ? "Tu peso se mantiene estable"
      : `Tu peso ${w.direction === "baja" ? "baja" : "sube"} ${fmt(w.perWeek)} kg/semana`;
  // Lectura de composición: qué se está moviendo realmente.
  if (fat && fat.direction === "baja" && (!muscle || muscle.direction !== "baja"))
    return `${base}, con la grasa bajando${muscle?.direction === "sube" ? " y el músculo subiendo" : ""}. Buena señal.`;
  if (fat && fat.direction === "sube" && w.direction !== "baja") return `${base} y el % graso sube: vigila el superávit.`;
  if (muscle && muscle.direction === "baja" && w.direction === "baja")
    return `${base}, pero también baja el músculo: revisa proteína y fuerza.`;
  return `${base}.`;
}

function goalStatus(
  goal: NutritionGoal | null,
  w: SeriesTrend | null,
  latestKg: number | null,
  latestIso: string | null,
  todayIso: string,
): BodyTrend["goal"] {
  if (!goal || !w || latestKg === null || latestIso === null) return null;
  const target = goal.targetWeightKg ?? null;
  if (target !== null) {
    const remaining = target - latestKg;
    if (Math.abs(remaining) < 0.3) return { tone: "ok", text: `Estás en tu peso objetivo (${fmt(target)} kg).` };
    const wrongWay = w.direction !== "estable" && Math.sign(w.perWeek) !== Math.sign(remaining);
    if (wrongWay)
      return { tone: "bad", text: `Vas en dirección contraria al objetivo de ${fmt(target)} kg (te quedan ${fmt(remaining)} kg).` };
    if (w.direction === "estable")
      return { tone: "warn", text: `Te quedan ${fmt(remaining)} kg para ${fmt(target)} kg, pero ahora mismo estás estancado.` };
    const weeks = remaining / w.perWeek;
    const eta = addWeeks(latestIso, weeks);
    if (goal.targetDate) {
      const weeksLeft = (dayNum(goal.targetDate) - dayNum(todayIso)) / 7;
      if (weeksLeft <= 0) return { tone: "warn", text: `La fecha objetivo ya pasó; te quedan ${fmt(remaining)} kg.` };
      const needed = remaining / weeksLeft;
      if (eta <= goal.targetDate)
        return { tone: "ok", text: `A este ritmo llegas a ${fmt(target)} kg el ${shortEs(eta)}, antes del ${shortEs(goal.targetDate)}.` };
      return {
        tone: "warn",
        text: `A este ritmo llegas el ${shortEs(eta)}, tarde para el ${shortEs(goal.targetDate)}: necesitas ${fmt(needed)} kg/semana.`,
      };
    }
    return { tone: "ok", text: `A este ritmo llegas a ${fmt(target)} kg hacia el ${shortEs(eta)} (faltan ${fmt(remaining)} kg).` };
  }
  if (goal.goal === "perder" || goal.goal === "corte")
    return w.direction === "baja"
      ? { tone: "ok", text: "Vas en la dirección de tu objetivo: perder peso." }
      : { tone: "warn", text: "Tu objetivo es perder peso, pero ahora mismo no baja." };
  if (goal.goal === "ganar")
    return w.direction === "sube"
      ? { tone: "ok", text: "Vas en la dirección de tu objetivo: ganar peso." }
      : { tone: "warn", text: "Tu objetivo es ganar peso, pero ahora mismo no sube." };
  return w.direction === "estable"
    ? { tone: "ok", text: "Objetivo mantener: tu peso está estable." }
    : { tone: "warn", text: `Objetivo mantener, pero tu peso ${w.direction} ${fmt(w.perWeek)} kg/semana.` };
}

export function bodyTrend(points: WeightPoint[], goal: NutritionGoal | null, todayIso: string): BodyTrend {
  const sorted = [...points].sort((a, b) => a.measuredOn.localeCompare(b.measuredOn));
  const weight = trendOf(sorted, (p) => p.weightKg, FLAT_KG_WEEK);
  const fat = trendOf(sorted, (p) => p.bodyFatPct, FLAT_PCT_WEEK);
  const muscle = trendOf(sorted, (p) => p.musclePct, FLAT_PCT_WEEK);
  const latest = sorted[sorted.length - 1] ?? null;
  return {
    weight,
    fat,
    muscle,
    summary: weightSummary(weight, fat, muscle),
    goal: goalStatus(goal, weight, latest?.weightKg ?? null, latest?.measuredOn ?? null, todayIso),
  };
}
