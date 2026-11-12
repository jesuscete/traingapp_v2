"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { Sheet } from "@/components/nutrition/Sheet";
import { errMsg, kcal, MEALS, parseNum } from "@/lib/nutrition";
import type { MealEntry, MealName } from "@/lib/types";

export function EditEntrySheet({
  token,
  entry,
  onClose,
  onChanged,
}: {
  token: string;
  entry: MealEntry;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [gramsText, setGramsText] = useState(entry.grams !== null ? String(entry.grams) : "");
  const [meal, setMeal] = useState<MealName>(entry.meal as MealName);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const newGrams = parseNum(gramsText);
  const gramsChanged = entry.grams !== null && Number.isFinite(newGrams) && newGrams !== entry.grams;
  const mealChanged = meal !== entry.meal;
  const gramsInvalid = entry.grams !== null && (!Number.isFinite(newGrams) || newGrams <= 0 || newGrams > 5000);
  const previewKcal =
    entry.grams !== null && Number.isFinite(newGrams) && newGrams > 0
      ? (entry.kcal / entry.grams) * newGrams
      : entry.kcal;

  async function save() {
    if (gramsInvalid || (!gramsChanged && !mealChanged)) return;
    setBusy(true);
    setError(null);
    try {
      await api.updateMealEntry(token, entry.id, {
        ...(mealChanged ? { meal } : {}),
        ...(gramsChanged ? { grams: newGrams } : {}),
      });
      onChanged();
      onClose();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar"));
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api.deleteMealEntry(token, entry.id);
      onChanged();
      onClose();
    } catch (err) {
      setError(errMsg(err, "No se pudo borrar"));
      setBusy(false);
    }
  }

  return (
    <Sheet title="Editar registro" onClose={onClose} compact>
      <div className="nu-form">
        <h4 className="nu-food-title">{entry.name}</h4>
        {entry.grams !== null ? (
          <label className="nu-field">
            <span>Gramos</span>
            <input
              type="text"
              inputMode="decimal"
              autoFocus
              value={gramsText}
              onChange={(e) => setGramsText(e.target.value)}
            />
          </label>
        ) : (
          <p className="muted nu-note">Registro rápido: solo se puede cambiar de comida o borrar.</p>
        )}
        {entry.grams !== null && entry.method === "racion" && gramsChanged && (
          <p className="muted nu-note">Al cambiar los gramos pasará a contar como pesada (exacta).</p>
        )}
        <label className="nu-field">
          <span>Comida</span>
          <select value={meal} onChange={(e) => setMeal(e.target.value as MealName)}>
            {MEALS.map((m) => (
              <option key={m.key} value={m.key}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <p className="nu-total">
          <strong>{kcal(previewKcal)} kcal</strong>
        </p>
        {error && <p className="error">{error}</p>}
        <div className="nu-actions">
          <button type="button" className="secondary nu-danger" disabled={busy} onClick={remove}>
            Borrar
          </button>
          <button type="button" disabled={busy || gramsInvalid || (!gramsChanged && !mealChanged)} onClick={save}>
            {busy ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </Sheet>
  );
}

export function TemplateNameSheet({
  token,
  entries,
  defaultName,
  onClose,
  onSaved,
}: {
  token: string;
  entries: MealEntry[];
  defaultName: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const items = entries.flatMap((e) =>
    e.foodId !== null && e.grams !== null ? [{ foodId: e.foodId, grams: e.grams }] : [],
  );
  const skipped = entries.length - items.length;
  const [name, setName] = useState(defaultName);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    if (!name.trim() || items.length === 0) return;
    setBusy(true);
    setError(null);
    try {
      await api.createMealTemplate(token, { name: name.trim(), items });
      onSaved();
      onClose();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar el plato"));
      setBusy(false);
    }
  }

  return (
    <Sheet title="Guardar como plato" onClose={onClose} compact>
      <div className="nu-form">
        <label className="nu-field">
          <span>Nombre del plato</span>
          <input type="text" autoFocus value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <p className="muted nu-note">
          {items.length} {items.length === 1 ? "alimento" : "alimentos"} con sus gramos.
          {skipped > 0 ? ` ${skipped} registro(s) rápidos no se incluyen.` : ""}
        </p>
        {error && <p className="error">{error}</p>}
        <button type="button" className="wk-primary" disabled={busy || !name.trim()} onClick={save}>
          {busy ? "Guardando…" : "Guardar plato"}
        </button>
      </div>
    </Sheet>
  );
}
