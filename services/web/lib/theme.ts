export const THEMES: { id: string; name: string }[] = [
  { id: "", name: "Por defecto (azul eléctrico)" },
  { id: "1", name: "Hierro nocturno" },
  { id: "2", name: "Pista azul" },
  { id: "3", name: "Tiza y grafito" },
  { id: "4", name: "Carbón y coral-cian" },
  { id: "5", name: "Negro suave y violeta eléctrico" },
];

const THEME_KEY = "traingapp_theme";

export function getTheme(): string {
  return localStorage.getItem(THEME_KEY) ?? "";
}

export function setTheme(themeId: string) {
  if (themeId) {
    localStorage.setItem(THEME_KEY, themeId);
    document.documentElement.dataset.theme = themeId;
  } else {
    localStorage.removeItem(THEME_KEY);
    delete document.documentElement.dataset.theme;
  }
}
