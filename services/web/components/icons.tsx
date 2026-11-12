import {
  Activity,
  Bike,
  Dumbbell,
  Footprints,
  Mountain,
  Swords,
  Waves,
  type LucideIcon,
} from "lucide-react";

const DISCIPLINE_ICONS: Record<string, LucideIcon> = {
  gym: Dumbbell,
  calisthenics: Dumbbell,
  running: Footprints,
  cycling: Bike,
  swimming: Waves,
  boxing: Swords,
  martial_arts: Swords,
  walking: Mountain,
  hiking: Mountain,
  climbing: Mountain,
};

export function DisciplineIcon({
  discipline,
  size = 20,
}: {
  discipline: string | null | undefined;
  size?: number;
}) {
  const Icon = (discipline && DISCIPLINE_ICONS[discipline]) || Activity;
  return <Icon size={size} strokeWidth={1.75} aria-hidden="true" />;
}

/** Mapea el deporte principal (texto libre del perfil) a una disciplina para el icono. */
export function sportToDiscipline(sport: string | null | undefined): string {
  const s = (sport ?? "").toLowerCase();
  if (/box|kick|muay|marcial/.test(s)) return "boxing";
  if (/tri|run|carrer/.test(s)) return "running";
  if (/cicl|bici/.test(s)) return "cycling";
  if (/nata|swim/.test(s)) return "swimming";
  if (/gim|fuerz|gym/.test(s)) return "gym";
  return "other";
}
