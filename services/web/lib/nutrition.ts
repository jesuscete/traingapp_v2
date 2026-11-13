import type { Food, MealMethod, MealName, ProposedItem } from "@/lib/types";

export const MEALS: { key: MealName; label: string }[] = [
  { key: "desayuno", label: "Desayuno" },
  { key: "media_manana", label: "Media mañana" },
  { key: "comida", label: "Comida" },
  { key: "merienda", label: "Merienda" },
  { key: "cena", label: "Cena" },
];

/** Registro agregado de todo el día (fuera de MEALS: no se elige como comida). */
export const DAY_MEAL: { key: MealName; label: string } = { key: "dia", label: "Día completo" };

export function defaultMealForNow(): MealName {
  const h = new Date().getHours();
  if (h < 10) return "desayuno";
  if (h < 13) return "media_manana";
  if (h < 16) return "comida";
  if (h < 20) return "merienda";
  return "cena";
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function todayISO(): string {
  return toISODate(new Date());
}

export function parseISODate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function shiftDay(iso: string, delta: number): string {
  const d = parseISODate(iso);
  d.setDate(d.getDate() + delta);
  return toISODate(d);
}

export function dayLabel(iso: string): string {
  const today = todayISO();
  if (iso === today) return "Hoy";
  if (iso === shiftDay(today, -1)) return "Ayer";
  if (iso === shiftDay(today, 1)) return "Mañana";
  return parseISODate(iso).toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
  });
}

export function shortDate(iso: string): string {
  return parseISODate(iso).toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

export function isExactMethod(method: string): boolean {
  return method === "pesada" || method === "etiqueta";
}

export const METHOD_LABELS: Record<MealMethod, string> = {
  pesada: "pesada",
  etiqueta: "etiqueta",
  racion: "ración",
  rapida: "rápida",
  ia: "IA",
};

export function methodLabel(method: string): string {
  return METHOD_LABELS[method as MealMethod] ?? method;
}

export function kcal(n: number): string {
  return String(Math.round(n));
}

export function g1(n: number): string {
  return (Math.round(n * 10) / 10).toString().replace(".", ",");
}

export type Macros = { kcal: number; proteinG: number; carbsG: number; fatG: number };

export function macrosFor(
  per100: { kcal100g: number; protein100g: number; carbs100g: number; fat100g: number },
  grams: number,
): Macros {
  const f = grams / 100;
  return {
    kcal: per100.kcal100g * f,
    proteinG: per100.protein100g * f,
    carbsG: per100.carbs100g * f,
    fatG: per100.fat100g * f,
  };
}

export function foodMacros(food: Food, grams: number): Macros {
  return macrosFor(food, grams);
}

export function itemMacros(item: ProposedItem): Macros {
  return macrosFor(item, item.grams);
}

export function sourceLabel(source: string): string {
  switch (source) {
    case "usda":
      return "USDA";
    case "custom":
      return "Tu alimento";
    case "off":
      return "Open Food Facts";
    default:
      return "Estimado IA";
  }
}

/** Número desde un input (acepta coma decimal); NaN si vacío o inválido. */
export function parseNum(value: string): number {
  const n = Number(value.trim().replace(",", "."));
  return value.trim() === "" ? Number.NaN : n;
}

export function errMsg(err: unknown, fallback: string): string {
  return err instanceof Error && err.message ? err.message : fallback;
}
