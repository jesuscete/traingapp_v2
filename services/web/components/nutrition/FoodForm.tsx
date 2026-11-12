"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { errMsg, parseNum } from "@/lib/nutrition";
import type { Food, Serving } from "@/lib/types";

type Props = {
  token: string;
  initialBarcode?: string;
  initialName?: string;
  onCreated: (food: Food) => void;
  onCancel: () => void;
};

type ServingRow = { label: string; grams: string };

function optional(value: string): number | null {
  const n = parseNum(value);
  return Number.isFinite(n) ? n : null;
}

export function FoodForm({ token, initialBarcode, initialName, onCreated, onCancel }: Props) {
  const [name, setName] = useState(initialName ?? "");
  const [brand, setBrand] = useState("");
  const [barcode, setBarcode] = useState(initialBarcode ?? "");
  const [kcalText, setKcalText] = useState("");
  const [protein, setProtein] = useState("");
  const [carbs, setCarbs] = useState("");
  const [fat, setFat] = useState("");
  const [fiber, setFiber] = useState("");
  const [sugar, setSugar] = useState("");
  const [servings, setServings] = useState<ServingRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateServing(i: number, patch: Partial<ServingRow>) {
    setServings((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const kcalN = parseNum(kcalText);
    if (!name.trim()) return setError("Pon un nombre.");
    if (!Number.isFinite(kcalN) || kcalN < 0 || kcalN > 950)
      return setError("Las kcal por 100 g deben estar entre 0 y 950.");
    const p = optional(protein) ?? 0;
    const c = optional(carbs) ?? 0;
    const f = optional(fat) ?? 0;
    const extra = [optional(fiber), optional(sugar)].filter((v): v is number => v !== null);
    if ([p, c, f, ...extra].some((v) => v < 0 || v > 100))
      return setError("Los macros por 100 g deben estar entre 0 y 100.");
    const servingList: Serving[] = [];
    for (const row of servings) {
      if (!row.label.trim() && !row.grams.trim()) continue;
      const gr = parseNum(row.grams);
      if (!row.label.trim() || !Number.isFinite(gr) || gr <= 0)
        return setError("Cada ración necesita nombre y gramos.");
      servingList.push({ label: row.label.trim(), grams: gr });
    }
    setBusy(true);
    setError(null);
    try {
      const food = await api.createFood(token, {
        name: name.trim(),
        brand: brand.trim() || null,
        barcode: barcode.trim() || null,
        kcal100g: kcalN,
        protein100g: p,
        carbs100g: c,
        fat100g: f,
        fiber100g: optional(fiber),
        sugar100g: optional(sugar),
        servings: servingList,
      });
      onCreated(food);
    } catch (err) {
      setError(errMsg(err, "No se pudo crear el alimento"));
      setBusy(false);
    }
  }

  return (
    <form className="nu-form" onSubmit={submit}>
      <button type="button" className="secondary nu-back" onClick={onCancel}>
        ← Volver
      </button>
      <h4 className="nu-food-title">Crear alimento (etiqueta)</h4>
      <p className="muted nu-note">Copia los valores de la etiqueta, siempre por 100 g.</p>
      <label className="nu-field">
        <span>Nombre</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} required />
      </label>
      <label className="nu-field">
        <span>Marca (opcional)</span>
        <input type="text" value={brand} onChange={(e) => setBrand(e.target.value)} />
      </label>
      <label className="nu-field">
        <span>Código de barras (opcional)</span>
        <input
          type="text"
          inputMode="numeric"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value.replace(/\D/g, ""))}
        />
      </label>
      <div className="nu-grid2">
        <label className="nu-field">
          <span>kcal / 100 g</span>
          <input type="text" inputMode="decimal" value={kcalText} onChange={(e) => setKcalText(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>Proteína (g)</span>
          <input type="text" inputMode="decimal" value={protein} onChange={(e) => setProtein(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>Hidratos (g)</span>
          <input type="text" inputMode="decimal" value={carbs} onChange={(e) => setCarbs(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>Grasas (g)</span>
          <input type="text" inputMode="decimal" value={fat} onChange={(e) => setFat(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>Fibra (g, opc.)</span>
          <input type="text" inputMode="decimal" value={fiber} onChange={(e) => setFiber(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>Azúcares (g, opc.)</span>
          <input type="text" inputMode="decimal" value={sugar} onChange={(e) => setSugar(e.target.value)} />
        </label>
      </div>

      <div className="nu-servings">
        <span className="muted">Raciones (opcional)</span>
        {servings.map((row, i) => (
          <div key={i} className="nu-serving-row">
            <input
              type="text"
              placeholder="Ej.: 1 rebanada"
              value={row.label}
              onChange={(e) => updateServing(i, { label: e.target.value })}
            />
            <input
              type="text"
              inputMode="decimal"
              placeholder="g"
              value={row.grams}
              onChange={(e) => updateServing(i, { grams: e.target.value })}
            />
            <button
              type="button"
              className="secondary nu-icon-btn"
              aria-label="Quitar ración"
              onClick={() => setServings((rows) => rows.filter((_, idx) => idx !== i))}
            >
              ✕
            </button>
          </div>
        ))}
        {servings.length < 10 && (
          <button
            type="button"
            className="secondary nu-add-link"
            onClick={() => setServings((rows) => [...rows, { label: "", grams: "" }])}
          >
            + Añadir ración
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      <button type="submit" className="wk-primary" disabled={busy}>
        {busy ? "Guardando…" : "Crear alimento"}
      </button>
    </form>
  );
}
