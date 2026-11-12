"use client";

import { g1, isExactMethod, kcal, methodLabel } from "@/lib/nutrition";
import type { MealEntry } from "@/lib/types";

type Props = {
  label: string;
  entries: MealEntry[];
  onAdd: () => void;
  onEdit: (entry: MealEntry) => void;
  onDelete: (entry: MealEntry) => void;
  onSaveTemplate: () => void;
};

export function MealSection({ label, entries, onAdd, onEdit, onDelete, onSaveTemplate }: Props) {
  const total = entries.reduce((acc, e) => acc + e.kcal, 0);
  const canTemplate = entries.some((e) => e.foodId !== null && e.grams !== null);

  return (
    <section className="block nu-meal">
      <header className="nu-meal-head">
        <h2>{label}</h2>
        <span className="nu-meal-kcal">{entries.length > 0 ? `${kcal(total)} kcal` : ""}</span>
        <button type="button" className="nu-add-btn" aria-label={`Añadir a ${label}`} onClick={onAdd}>
          +
        </button>
      </header>
      {entries.length === 0 ? (
        <p className="muted nu-empty">Sin registros</p>
      ) : (
        <ul className="nu-entries">
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
                  ✕
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {canTemplate && (
        <button type="button" className="secondary nu-add-link" onClick={onSaveTemplate}>
          Guardar como plato
        </button>
      )}
    </section>
  );
}
