import { Flag, Scale, Target, Trophy } from "lucide-react";

import type { GoalKind } from "@/lib/types";

export const GOAL_KIND_LABELS: Record<GoalKind, string> = {
  weight: "Peso",
  event: "Prueba / carrera",
  competition: "Competición / combate",
  performance: "Marca",
  other: "Otro",
};

export function GoalKindIcon({ kind, size = 22 }: { kind: GoalKind; size?: number }) {
  const props = { size, strokeWidth: 1.75, "aria-hidden": true } as const;
  if (kind === "weight") return <Scale {...props} />;
  if (kind === "event") return <Flag {...props} />;
  if (kind === "competition") return <Trophy {...props} />;
  return <Target {...props} />;
}

export function countdownLabel(daysLeft: number | null | undefined): string | null {
  if (daysLeft == null) return null;
  if (daysLeft === 0) return "Hoy";
  if (daysLeft < 0) return "Pasada";
  return `Faltan ${daysLeft} ${daysLeft === 1 ? "día" : "días"}`;
}

