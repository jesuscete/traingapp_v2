import type { ComponentType, ReactNode } from "react";
import {
  Activity,
  Bike,
  Dumbbell,
  Footprints,
  Mountain,
  Snowflake,
  Swords,
  Volleyball,
  Waves,
} from "lucide-react";

type IconProps = { size?: number; strokeWidth?: number; "aria-hidden"?: boolean | "true" | "false" };

/** Iconos propios con la misma rejilla y trazo que lucide (24×24, línea redondeada). */
function lineIcon(children: ReactNode): ComponentType<IconProps> {
  return function LineIcon({ size = 24, strokeWidth = 2, ...rest }: IconProps) {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        {...rest}
      >
        {children}
      </svg>
    );
  };
}

export const Kettlebell = lineIcon(
  <>
    <path d="M9 11.2 7.9 6.3A1.5 1.5 0 0 1 9.4 4.5h5.2a1.5 1.5 0 0 1 1.5 1.8L15 11.2" />
    <path d="M6.8 20.5a6.5 6.5 0 1 1 10.4 0z" />
  </>,
);

export const BoxingGlove = lineIcon(
  <>
    <path d="M8 17h7.5a2.5 2.5 0 0 0 2.5-2.5V8a4 4 0 0 0-4-4h-2.5A4.5 4.5 0 0 0 7 8.5V11" />
    <path d="M7 10.5a2.25 2.25 0 0 0 0 4.5h3" />
    <path d="M8 17v3.5h8V17" />
  </>,
);

export const SoccerBall = lineIcon(
  <>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 8.8l3 2.2-1.1 3.6h-3.8L9 11z" />
    <path d="M12 8.8V3M15 11l5.5-1.8M13.9 14.6l3.4 4.7M10.1 14.6l-3.4 4.7M9 11L3.5 9.2" />
  </>,
);

const DISCIPLINE_ICONS: Record<string, ComponentType<IconProps>> = {
  gym: Dumbbell,
  calisthenics: Dumbbell,
  crossfit: Kettlebell,
  hyrox: Kettlebell,
  running: Footprints,
  cycling: Bike,
  swimming: Waves,
  boxing: BoxingGlove,
  martial_arts: Swords,
  football: SoccerBall,
  volleyball: Volleyball,
  basketball: Volleyball,
  handball: Volleyball,
  walking: Mountain,
  hiking: Mountain,
  climbing: Mountain,
  ski_snowboard: Snowflake,
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
  if (/hyrox/.test(s)) return "hyrox";
  if (/crossfit/.test(s)) return "crossfit";
  if (/box|kick|muay/.test(s)) return "boxing";
  if (/marcial/.test(s)) return "martial_arts";
  if (/f[uú]tbol|soccer/.test(s)) return "football";
  if (/tri|run|carrer/.test(s)) return "running";
  if (/cicl|bici/.test(s)) return "cycling";
  if (/nata|swim/.test(s)) return "swimming";
  if (/gim|fuerz|gym/.test(s)) return "gym";
  return "other";
}
