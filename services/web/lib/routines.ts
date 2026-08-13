import type { DayType } from "@/lib/types";

export const WEEKDAYS = [
  "Lunes",
  "Martes",
  "Miércoles",
  "Jueves",
  "Viernes",
  "Sábado",
  "Domingo",
];

export const DAY_TYPE_LABELS: Record<DayType, string> = {
  gimnasio: "Gimnasio",
  deporte: "Deporte",
  descanso: "Descanso",
};

export const DAY_TYPE_OPTIONS: DayType[] = ["gimnasio", "deporte", "descanso"];
