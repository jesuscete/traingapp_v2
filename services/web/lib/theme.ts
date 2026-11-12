/**
 * Tema = modo (oscuro / claro / automático) + color de marca. Se guarda en el navegador y se
 * aplica como html[data-mode] y html[data-accent] (ver styles/tokens.css). El script de
 * `THEME_BOOT_SCRIPT` lo aplica antes de pintar para que no haya parpadeo.
 */

export type ThemeMode = "dark" | "light" | "auto";

export const MODES: { id: ThemeMode; name: string }[] = [
  { id: "dark", name: "Oscuro" },
  { id: "light", name: "Claro" },
  { id: "auto", name: "Automático" },
];

export const ACCENTS: { id: string; name: string; swatch: string }[] = [
  { id: "azul", name: "Azul eléctrico", swatch: "#3b82f6" },
  { id: "naranja", name: "Naranja combate", swatch: "#ff6b3d" },
  { id: "rojo", name: "Rojo intenso", swatch: "#f43f5e" },
  { id: "verde", name: "Verde energía", swatch: "#22c55e" },
  { id: "violeta", name: "Violeta", swatch: "#8b5cf6" },
  { id: "cian", name: "Cian", swatch: "#22d3ee" },
  { id: "ambar", name: "Ámbar", swatch: "#f59e0b" },
  { id: "lima", name: "Lima", swatch: "#a3e635" },
  { id: "grafito", name: "Grafito (sobrio)", swatch: "#9ca3af" },
];

const MODE_KEY = "traingapp_mode";
const ACCENT_KEY = "traingapp_accent";
const LEGACY_KEY = "traingapp_theme";
// Temas antiguos (selector de 5 paletas) → modo + color equivalentes.
const LEGACY: Record<string, [ThemeMode, string]> = {
  "1": ["dark", "naranja"],
  "2": ["dark", "azul"],
  "3": ["light", "grafito"],
  "4": ["dark", "rojo"],
  "5": ["dark", "violeta"],
};

export type ThemePrefs = { mode: ThemeMode; accent: string };

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // almacenamiento no disponible: el tema solo dura esta visita
  }
}

export function getThemePrefs(): ThemePrefs {
  const legacy = read(LEGACY_KEY);
  if (legacy && LEGACY[legacy] && !read(MODE_KEY)) {
    const [mode, accent] = LEGACY[legacy];
    write(MODE_KEY, mode);
    write(ACCENT_KEY, accent);
  }
  const mode = (read(MODE_KEY) as ThemeMode | null) ?? "dark";
  const accent = read(ACCENT_KEY) ?? "azul";
  return {
    mode: MODES.some((m) => m.id === mode) ? mode : "dark",
    accent: ACCENTS.some((a) => a.id === accent) ? accent : "azul",
  };
}

function resolvedMode(mode: ThemeMode): "dark" | "light" {
  if (mode !== "auto") return mode;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function applyTheme(prefs: ThemePrefs = getThemePrefs()): void {
  const root = document.documentElement;
  const mode = resolvedMode(prefs.mode);
  root.dataset.mode = mode;
  root.dataset.accent = prefs.accent;
  delete root.dataset.theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", mode === "light" ? "#f5f6f8" : "#121317");
}

export function setThemeMode(mode: ThemeMode): void {
  write(MODE_KEY, mode);
  applyTheme();
}

export function setThemeAccent(accent: string): void {
  write(ACCENT_KEY, accent);
  applyTheme();
}

/** Se inyecta en <head>: aplica el tema guardado antes del primer pintado. */
export const THEME_BOOT_SCRIPT = `(function(){try{var L={"1":["dark","naranja"],"2":["dark","azul"],"3":["light","grafito"],"4":["dark","rojo"],"5":["dark","violeta"]};var s=localStorage,m=s.getItem("${MODE_KEY}"),a=s.getItem("${ACCENT_KEY}"),o=s.getItem("${LEGACY_KEY}");if(!m&&o&&L[o]){m=L[o][0];a=L[o][1];}m=m||"dark";a=a||"azul";if(m==="auto"){m=window.matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";}var r=document.documentElement;r.setAttribute("data-mode",m);r.setAttribute("data-accent",a);}catch(e){}})();`;
