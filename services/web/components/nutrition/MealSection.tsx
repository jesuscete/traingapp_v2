"use client";

import { useEffect, useState } from "react";
import { ChevronDown, X } from "lucide-react";

import { g1, isExactMethod, kcal, methodLabel } from "@/lib/nutrition";
import type { MealEntry } from "@/lib/types";

const OPEN_KEY = "traingapp_meal_open_v1";

function readOpen(): Record<string, boolean> {
  try {
    const raw = localStorage.getItem(OPEN_KEY);
    return raw ? (JSON.parse(raw) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function writeOpen(id: string, open: boolean): void {
  try {
    localStorage.setItem(OPEN_KEY, JSON.stringify({ ...readOpen(), [id]: open }));
  } catch {
    // sin localStorage: el estado solo dura mientras la página esté abierta
  }
}

type Props = {
  /** Clave estable para recordar si está desplegada. */
  id: string;
  label: string;
  /** kcal totales del día, para mostrar el reparto. */
  dayKcal: number;
  entries: MealEntry[];
  onAdd: () => void;
  onEdit: (entry: MealEntry) => void;
  onDelete: (entry: MealEntry) => void;
  onSaveTemplate: () => void;
};

export function MealSection({ id, label, dayKcal, entries, onAdd, onEdit, onDelete, onSaveTemplate }: Props) {
  const total = entries.reduce((acc, e) => acc + e.kcal, 0);
  const share = dayKcal > 0 ? Math.round((total / dayKcal) * 100) : 0;
  const canTemplate = entries.some((e) => e.foodId !== null && e.grams !== null);
  // Plegadas por defecto: de un vistazo se ve el reparto de kcal entre comidas.
  const [open, setOpen] = useState(false);
  useEffect(() => {
    setOpen(readOpen()[id] ?? false);
  }, [id]);

  function toggle() {
    setOpen((value) => {
      writeOpen(id, !value);
      return !value;
    });
  }

  return (
    <section className={`block nu-meal${open ? " open" : ""}`}>
      <header className="nu-meal-head">
        <button
          type="button"
          className="nu-meal-toggle"
          aria-expanded={open}
          aria-controls={`meal-${id}`}
          onClick={toggle}
        >
          <ChevronDown className="nu-meal-chevron" size={20} strokeWidth={1.75} aria-hidden="true" />
          <span className="nu-meal-title">
            <h2>{label}</h2>
            <span className="muted nu-meal-count">
              {entries.length === 0 ? "Sin registros" : `${entries.length} ${entries.length === 1 ? "alimento" : "alimentos"}`}
            </span>
          </span>
          <span className="nu-meal-kcal">
            <strong>{entries.length > 0 ? kcal(total) : "—"}</strong>
            {entries.length > 0 && <span className="muted"> kcal · {share}%</span>}
          </span>
        </button>
        <button type="button" className="nu-add-btn" aria-label={`Añadir a ${label}`} onClick={onAdd}>
          +
        </button>
      </header>
      <div className="nu-meal-share" aria-hidden="true">
        <div style={{ width: `${Math.min(100, share)}%` }} />
      </div>
      {!open ? null : entries.length === 0 ? (
        <p id={`meal-${id}`} className="muted nu-empty">Sin registros</p>
      ) : (
        <ul id={`meal-${id}`} className="nu-entries">
          {entries.map((e) => {
            const exact = isExactMethod(e.method);
            return (
              <li key={e.id} className="nu-entry">
                <button type="button" className="nu-entry-main" onClick={() => onEdit(e)}>
                  <span className="nu-entry-name">{e.name}</span>
                  <span className="muted nu-entry-sub">
                    {e.grams !== null ? `${g1(e.grams)} g · ` : ""}P {g1(e.proteinG)} · H {g1(e.carbsG)} · G{" "}
                    {g1(e.fatG)}
                  </span>
                </button>
                <span className="nu-entry-right">
                  <strong>{kcal(e.kcal)}</strong>
                  <span className={`nu-badge ${exact ? "nu-exact-badge" : "nu-est-badge"}`}>
                    {methodLabel(e.method)}
                  </span>
                </span>
                <button
                  type="button"
                  className="secondary nu-icon-btn"
                  aria-label={`Borrar ${e.name}`}
                  onClick={() => onDelete(e)}
                >
                  <X size={18} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {open && canTemplate && (
        <button type="button" className="secondary nu-add-link" onClick={onSaveTemplate}>
          Guardar como plato
        </button>
      )}
    </section>
  );
}
