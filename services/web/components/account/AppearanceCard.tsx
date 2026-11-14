"use client";

import { Check } from "lucide-react";
import { useEffect, useState } from "react";

import { DEFAULT_THEME, getThemeId, setTheme, THEMES } from "@/lib/theme";

export function AppearanceCard() {
  const [current, setCurrent] = useState<string>(DEFAULT_THEME);

  useEffect(() => {
    setCurrent(getThemeId());
  }, []);

  return (
    <section className="energy-card appearance-card">
      <h3>Apariencia</h3>
      <p className="subtitle">Se guarda en este navegador y se aplica al instante.</p>

      <h4 className="appearance-label">Tema</h4>
      <div className="theme-list" role="radiogroup" aria-label="Tema">
        {THEMES.map((t) => {
          const selected = current === t.id;
          return (
            <button
              key={t.id}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`theme-option${selected ? " selected" : ""}`}
              onClick={() => {
                setTheme(t.id);
                setCurrent(t.id);
              }}
            >
              <span className="theme-swatches" aria-hidden="true">
                {t.swatches.map((c) => (
                  <span key={c} style={{ background: c }} />
                ))}
              </span>
              <span className="theme-name">{t.name}</span>
              {selected && <Check size={20} strokeWidth={2.5} aria-hidden="true" />}
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
