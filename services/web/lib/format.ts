export function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null || minutes <= 0) return "—";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (h === 0) return `${m} min`;
  if (m === 0) return `${h} h`;
  return `${h} h ${m} min`;
}

export function formatKcal(kcal: number | null | undefined): string {
  if (kcal == null || kcal <= 0) return "—";
  return `${Math.round(kcal)} kcal`;
}

const FREE_EXERCISE_DB_IMAGE_BASE =
  "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/";

export function exerciseImageUrl(
  path: string | null | undefined,
): string | null {
  if (!path) return null;
  return `${FREE_EXERCISE_DB_IMAGE_BASE}${path}`;
}

export type ZoneRadarPoint = { label: string; value: number };

export function aggregateByZone<T extends { zone?: string | null }>(
  items: T[],
  valueOf: (item: T) => number,
  mode: "sum" | "mean" = "sum",
): ZoneRadarPoint[] {
  const totals = new Map<string, number>();
  const counts = new Map<string, number>();
  for (const item of items) {
    const zone = item.zone || "other";
    totals.set(zone, (totals.get(zone) ?? 0) + valueOf(item));
    counts.set(zone, (counts.get(zone) ?? 0) + 1);
  }
  const entries = [...totals.entries()]
    .map(([zone, total]) => [
      zone,
      mode === "mean" ? total / (counts.get(zone) ?? 1) : total,
    ] as const)
    .filter(([, value]) => value > 0)
    .sort((a, b) => b[1] - a[1]);
  const max = entries[0]?.[1] ?? 0;
  return entries.map(([zone, value]) => ({
    label: zone,
    value: max ? value / max : 0,
  }));
}
