export const MUSCLE_GROUP_LABELS: Record<string, string> = {
  quadriceps: "Cuádriceps",
  hamstrings: "Isquios",
  glutes: "Glúteos",
  calves: "Gemelos",
  core: "Core",
  back: "Espalda",
  chest: "Pecho",
  shoulders: "Hombros",
  biceps: "Bíceps",
  triceps: "Tríceps",
  forearms: "Antebrazos",
  neck: "Cuello",
  legs: "Piernas",
  arms: "Brazos",
};

export const DISCIPLINE_LABELS: Record<string, string> = {
  gym: "Gimnasio",
  boxing: "Boxeo",
  running: "Running",
  cycling: "Ciclismo",
  swimming: "Natación",
  other: "Otro",
  football: "Fútbol",
  badminton: "Bádminton",
  basketball: "Baloncesto",
  table_tennis: "Tenis de mesa",
  volleyball: "Voleibol",
  tennis: "Tenis",
  cricket: "Cricket",
  golf: "Golf",
  baseball: "Béisbol",
  martial_arts: "Artes marciales",
  hockey: "Hockey",
  rugby: "Rugby",
  handball: "Balonmano",
  climbing: "Escalada",
  ski_snowboard: "Esquí / snowboard",
  calisthenics: "Calistenia",
};

const INSIGHT_TOKEN_MAP: Record<string, string> = {
  ...MUSCLE_GROUP_LABELS,
  ...DISCIPLINE_LABELS,
};

export function translateMuscleGroup(key: string | null | undefined): string {
  if (!key) return "—";
  return MUSCLE_GROUP_LABELS[key] ?? key;
}

export function translateDiscipline(key: string | null | undefined): string {
  if (!key) return "—";
  return DISCIPLINE_LABELS[key] ?? key;
}

export function translateInsightMessage(message: string): string {
  return message.replace(
    /\b(chest|back|shoulders|legs|arms|core|gym|boxing|running|cycling|swimming)\b/g,
    (token) => INSIGHT_TOKEN_MAP[token] ?? token,
  );
}
