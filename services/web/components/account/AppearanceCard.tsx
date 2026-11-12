"use client";

import { Check } from "lucide-react";
import { useEffect, useState } from "react";

import { ACCENTS, getThemePrefs, MODES, setThemeAccent, setThemeMode, type ThemePrefs } from "@/lib/theme";

export function AppearanceCard() {
  const [prefs, setPrefs] = useState<ThemePrefs>({ mode: "dark", accent: "azul" });

  useEffect(() => {
    setPrefs(getThemePrefs());
  }, []);

  return (
    <section className="energy-card appearance-card">
      <h3>Apariencia</h3>
      <p className="subtitle">Se guarda en este navegador y se aplica al instante.</p>

      <h4 className="appearance-label">Modo</h4>
      <div className="segmented" role="group" aria-label="Modo">
        {MODES.map((m) => (
          <button
            key={m.id}
            type="button"
            className={`segmented-btn${prefs.mode === m.id ? " active" : ""}`}
            aria-pressed={prefs.mode === m.id}
            onClick={() => {
              setThemeMode(m.id);
              setPrefs((p) => ({ ...p, mode: m.id }));
            }}
          >
            {m.name}
          </button>
        ))}
      </div>

      <h4 className="appearance-label">Color</h4>
      <div className="swatch-grid" role="group" aria-label="Color">
        {ACCENTS.map((a) => {
          const selected = prefs.accent === a.id;
          return (
            <button
              key={a.id}
              type="button"
              className={`swatch${selected ? " selected" : ""}`}
              style={{ background: a.swatch }}
              aria-label={a.name}
              aria-pressed={selected}
              title={a.name}
              onClick={() => {
                setThemeAccent(a.id);
                setPrefs((p) => ({ ...p, accent: a.id }));
              }}
            >
              {selected && <Check size={20} strokeWidth={3} aria-hidden="true" />}
            </button>
          );
        })}
      </div>

      <h4 className="appearance-label">Vista previa</h4>
      <div className="appearance-preview">
        <button type="button" className="appearance-preview-btn">Botón principal</button>
        <span className="appearance-preview-chip">Etiqueta</span>
        <div className="appearance-preview-bar" aria-hidden="true"><span /></div>
      </div>
    </section>
  );
}
