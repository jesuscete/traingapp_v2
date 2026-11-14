/**
 * Tema visual completo (fondo, superficies, acento y texto). Se guarda en el navegador y se
 * aplica como html[data-theme] (ver styles/tokens.css). `THEME_BOOT_SCRIPT` lo aplica antes de
 * pintar para que no haya parpadeo. Son temas en prueba hasta decidir la estética definitiva.
 */

export type Theme = {
  id: string;
  name: string;
  /** Base, superficie, acento, secundario y texto: para la muestra del selector. */
  swatches: [string, string, string, string, string];
  themeColor: string;
};

export const THEMES: Theme[] = [
  { id: "original", name: "Original", swatches: ["#121317", "#1b1d22", "#3b82f6", "#2fd9a8", "#f4f4f2"], themeColor: "#121317" },
  { id: "athlys", name: "Athlys", swatches: ["#101820", "#202e38", "#00cdb5", "#72dccb", "#f4f6f5"], themeColor: "#101820" },
  { id: "teal", name: "Midnight Teal", swatches: ["#101820", "#202e38", "#36bfa3", "#a6dccb", "#f1f4f2"], themeColor: "#101820" },
  { id: "iris", name: "Ink Iris", swatches: ["#171b24", "#343c4c", "#8584c7", "#b9b8e5", "#f3f1f6"], themeColor: "#171b24" },
  { id: "lima", name: "Forest Lime", swatches: ["#151c19", "#29372f", "#a6c66c", "#d1dfaf", "#f3f3ea"], themeColor: "#151c19" },
];

export const DEFAULT_THEME = "original";
const THEME_KEY = "athlys_theme";

function findTheme(id: string | null): Theme {
  return THEMES.find((t) => t.id === id) ?? THEMES.find((t) => t.id === DEFAULT_THEME)!;
}

export function getThemeId(): string {
  try {
    return findTheme(localStorage.getItem(THEME_KEY)).id;
  } catch {
    return DEFAULT_THEME;
  }
}

export function applyTheme(id: string = getThemeId()): void {
  const theme = findTheme(id);
  const root = document.documentElement;
  root.dataset.theme = theme.id;
  delete root.dataset.mode;
  delete root.dataset.accent;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme.themeColor);
}

export function setTheme(id: string): void {
  try {
    localStorage.setItem(THEME_KEY, id);
  } catch {
    // almacenamiento no disponible: el tema solo dura esta visita
  }
  applyTheme(id);
}

/** Se inyecta en <head>: aplica el tema guardado antes del primer pintado. */
export const THEME_BOOT_SCRIPT = `(function(){try{var ok=${JSON.stringify(THEMES.map((t) => t.id))};var t=localStorage.getItem("${THEME_KEY}");if(ok.indexOf(t)<0)t="${DEFAULT_THEME}";document.documentElement.setAttribute("data-theme",t);}catch(e){document.documentElement.setAttribute("data-theme","${DEFAULT_THEME}");}})();`;
