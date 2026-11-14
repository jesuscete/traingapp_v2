/** Lógica de macros sin IA: estado del día, barras proporcionales y consejo rápido. */

export type MacroKey = "protein" | "carbs" | "fat";

export type MacroTotals = { proteinG: number; carbsG: number; fatG: number };

const KCAL_PER_G: Record<MacroKey, number> = { protein: 4, carbs: 4, fat: 9 };
const LABELS: Record<MacroKey, string> = { protein: "Proteína", carbs: "Hidratos", fat: "Grasas" };
const KEYS: MacroKey[] = ["protein", "carbs", "fat"];
/** Margen antes de considerar que te has pasado (5 %). */
const OVER = 1.05;

function grams(t: MacroTotals, k: MacroKey): number {
  return k === "protein" ? t.proteinG : k === "carbs" ? t.carbsG : t.fatG;
}

export type DayStatus = "empty" | "progress" | "ok" | "low" | "high";

/** Estado de un día frente a su objetivo de kcal; el día en curso no se juzga si va por debajo. */
export function dayStatus(kcal: number, target: number | null, isToday: boolean): DayStatus {
  if (kcal <= 0) return "empty";
  if (!target) return "ok";
  const ratio = kcal / target;
  if (ratio > 1.1) return "high";
  if (ratio < 0.9) return isToday ? "progress" : "low";
  return "ok";
}

export type MacroBar = {
  key: MacroKey;
  label: string;
  value: number;
  target: number;
  /** % de las kcal objetivo que aporta este macro. */
  sharePct: number;
  /** Ancho de la pista (objetivo) en % del contenedor: proporcional al peso del macro. */
  trackPct: number;
  /** Parte llena hasta el objetivo, en % del contenedor. */
  fillPct: number;
  /** Exceso sobre el objetivo, en % del contenedor (tope visual). */
  overPct: number;
  over: boolean;
};

/** Hueco que se reserva a la derecha para dibujar el exceso. */
const OVERFLOW_ROOM = 25;

export function macroBars(totals: MacroTotals, target: MacroTotals): MacroBar[] {
  const kcalOf = (k: MacroKey) => grams(target, k) * KCAL_PER_G[k];
  const total = KEYS.reduce((acc, k) => acc + kcalOf(k), 0);
  if (total <= 0) return [];
  const maxShare = Math.max(...KEYS.map(kcalOf)) / total;
  return KEYS.map((key) => {
    const value = grams(totals, key);
    const goal = grams(target, key);
    const share = kcalOf(key) / total;
    const trackPct = (share / maxShare) * (100 - OVERFLOW_ROOM);
    const ratio = goal > 0 ? value / goal : 0;
    return {
      key,
      label: LABELS[key],
      value,
      target: goal,
      sharePct: Math.round(share * 100),
      trackPct,
      fillPct: Math.min(1, ratio) * trackPct,
      overPct: Math.min(OVERFLOW_ROOM, Math.max(0, ratio - 1) * trackPct),
      over: ratio > OVER,
    };
  });
}

/**
 * Una o dos frases para decidir la próxima comida. `hour` es la hora local:
 * por la mañana no tiene sentido avisar de que falta casi todo.
 */
export function macroAdvice(totals: MacroTotals, target: MacroTotals, hour: number): string | null {
  const left = (k: MacroKey) => grams(target, k) - grams(totals, k);
  const overs = KEYS.filter((k) => grams(target, k) > 0 && grams(totals, k) > grams(target, k) * OVER);
  const protLeft = left("protein");
  const parts: string[] = [];

  if (overs.length > 0) {
    const names = overs.map((k) => `${LABELS[k].toLowerCase()} (+${Math.round(-left(k))} g)`).join(" y ");
    parts.push(`Te has pasado en ${names}.`);
    if (protLeft > 15) parts.push(`Lo que queda, mejor proteico y con verdura: faltan ${Math.round(protLeft)} g de proteína.`);
    else parts.push("Lo que queda del día, ligero y con verdura.");
    return parts.join(" ");
  }
  if (hour < 12) return null;
  const consumedKcal = KEYS.reduce((acc, k) => acc + grams(totals, k) * KCAL_PER_G[k], 0);
  const targetKcal = KEYS.reduce((acc, k) => acc + grams(target, k) * KCAL_PER_G[k], 0);
  if (consumedKcal <= 0 || targetKcal <= 0) return null;
  // Proteína rezagada respecto al resto del día.
  const protRatio = grams(totals, "protein") / Math.max(1, grams(target, "protein"));
  const dayRatio = consumedKcal / targetKcal;
  if (protLeft > 20 && protRatio < dayRatio - 0.15) {
    return `Vas corto de proteína: faltan ${Math.round(protLeft)} g. Prioriza carne, pescado, huevos o lácteos en la próxima comida.`;
  }
  if (hour >= 18 && dayRatio < 0.7) {
    return `Aún te quedan ${Math.round(targetKcal - consumedKcal)} kcal: no te saltes la cena.`;
  }
  return null;
}
