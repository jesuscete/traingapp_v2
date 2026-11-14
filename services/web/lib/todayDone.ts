import { translateDiscipline } from "@/lib/labels";
import type { SessionSummary } from "@/lib/types";

export type TodayDone = {
  title: string;
  /** Disciplina del entreno principal (el más largo): decide el icono. */
  mainDiscipline: string;
  sessions: SessionSummary[];
  minutes: number;
  kcal: number;
  /** FC media ponderada por duración de las sesiones que la tienen. */
  avgHeartRate: number | null;
  volumeKg: number;
  distanceMeters: number;
};

/** «HYROX» y «CrossFit» se quedan; «Boxeo» pasa a «boxeo» dentro de la frase. */
export function inSentence(label: string): string {
  return /[A-ZÁÉÍÓÚÑ]/.test(label.slice(1)) ? label : label.toLowerCase();
}

function longestFirst(a: SessionSummary, b: SessionSummary): number {
  return (b.durationMinutes ?? 0) - (a.durationMinutes ?? 0);
}

/** Resumen de lo entrenado hoy; null si aún no hay nada registrado. */
export function summarizeToday(sessions: SessionSummary[]): TodayDone | null {
  if (sessions.length === 0) return null;
  const ordered = [...sessions].sort(longestFirst);
  const disciplines = [...new Set(ordered.map((s) => s.discipline))].filter((d) => d !== "other");
  const names = disciplines.map((d) => inSentence(translateDiscipline(d)));
  const title =
    names.length === 0
      ? "¡Buen entreno!"
      : names.length === 1
      ? `¡Buen entreno de ${names[0]}!`
      : `¡Buen día: ${names.slice(0, -1).join(", ")} y ${names[names.length - 1]}!`;

  let hrWeighted = 0;
  let hrMinutes = 0;
  for (const s of ordered) {
    if (s.avgHeartRate && s.durationMinutes) {
      hrWeighted += s.avgHeartRate * s.durationMinutes;
      hrMinutes += s.durationMinutes;
    }
  }
  const sum = (pick: (s: SessionSummary) => number | null | undefined) =>
    ordered.reduce((acc, s) => acc + (pick(s) ?? 0), 0);

  return {
    title,
    mainDiscipline: ordered[0].discipline,
    sessions: ordered,
    minutes: sum((s) => s.durationMinutes),
    kcal: sum((s) => s.estimatedKcal),
    avgHeartRate: hrMinutes > 0 ? Math.round(hrWeighted / hrMinutes) : null,
    volumeKg: sum((s) => s.volumeKg),
    distanceMeters: sum((s) => s.distanceMeters),
  };
}
