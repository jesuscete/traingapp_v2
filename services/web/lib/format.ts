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
