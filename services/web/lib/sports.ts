export type SportOption = { key: string; label: string };

export const MAIN_SPORTS: SportOption[] = [
  { key: "boxeo", label: "Boxeo" },
  { key: "kickboxing", label: "Kickboxing / Muay thai" },
  { key: "triatlon", label: "Triatlón" },
  { key: "running", label: "Running" },
  { key: "ciclismo", label: "Ciclismo" },
  { key: "natacion", label: "Natación" },
  { key: "gimnasio", label: "Gimnasio / fuerza" },
];

export const OTHER_SPORTS: SportOption[] = [...MAIN_SPORTS, { key: "otro", label: "Otro" }];
