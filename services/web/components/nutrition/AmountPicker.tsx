"use client";

import { useState } from "react";

import { foodMacros, g1, kcal, parseNum } from "@/lib/nutrition";
import type { Food } from "@/lib/types";

export type Amount =
  | { kind: "grams"; grams: number }
  | { kind: "servings"; servings: number; label: string };

type Props = {
  food: Food;
  busy: boolean;
  error: string | null;
  onConfirm: (amount: Amount) => void;
  onBack: () => void;
};

export function AmountPicker({ food, busy, error, onConfirm, onBack }: Props) {
  const hasServings = food.servings.length > 0;
  const [mode, setMode] = useState<"grams" | "servings">("grams");
  const [gramsText, setGramsText] = useState("");
  const [servingIdx, setServingIdx] = useState(0);
  const [servingsText, setServingsText] = useState("1");

  const serving = food.servings[servingIdx];
  const grams = parseNum(gramsText);
  const nServ = parseNum(servingsText);
  const effectiveGrams =
    mode === "grams" ? grams : serving && Number.isFinite(nServ) ? nServ * serving.grams : Number.NaN;
  const valid = Number.isFinite(effectiveGrams) && effectiveGrams > 0 && effectiveGrams <= 5000;
  const macros = valid ? foodMacros(food, effectiveGrams) : null;

  function submit() {
    if (!valid) return;
    if (mode === "grams") onConfirm({ kind: "grams", grams });
    else onConfirm({ kind: "servings", servings: nServ, label: serving.label });
  }

  return (
    <div className="nu-amount">
      <button type="button" className="secondary nu-back" onClick={onBack}>
        ← Volver
      </button>
      <h4 className="nu-food-title">{food.name}</h4>
      {food.brand && <p className="muted nu-food-brand">{food.brand}</p>}
      <p className="muted nu-per100">
        Por 100 g: {kcal(food.kcal100g)} kcal · P {g1(food.protein100g)} · H {g1(food.carbs100g)} · G{" "}
        {g1(food.fat100g)}
      </p>

      {hasServings && (
        <div className="nu-seg" role="tablist" aria-label="Unidad">
          <button
            type="button"
            className={mode === "grams" ? "active" : ""}
            onClick={() => setMode("grams")}
          >
            Gramos
          </button>
          <button
            type="button"
            className={mode === "servings" ? "active" : ""}
            onClick={() => setMode("servings")}
          >
            Raciones
          </button>
        </div>
      )}

      {mode === "grams" ? (
        <label className="nu-field">
          <span>Cantidad (g)</span>
          <input
            type="text"
            inputMode="decimal"
            autoFocus
            placeholder="0"
            value={gramsText}
            onChange={(e) => setGramsText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") submit();
            }}
          />
        </label>
      ) : (
        <>
          <label className="nu-field">
            <span>Ración</span>
            <select value={servingIdx} onChange={(e) => setServingIdx(Number(e.target.value))}>
              {food.servings.map((s, i) => (
                <option key={`${s.label}-${i}`} value={i}>
                  {s.label} ({Math.round(s.grams)} g)
                </option>
              ))}
            </select>
          </label>
          <label className="nu-field">
            <span>Nº de raciones</span>
            <input
              type="text"
              inputMode="decimal"
              value={servingsText}
              onChange={(e) => setServingsText(e.target.value)}
            />
          </label>
          <p className="muted nu-note">Las raciones son estimadas; pesar en gramos es más preciso.</p>
        </>
      )}

      <div className="nu-preview" aria-live="polite">
        <strong className="nu-preview-kcal">{macros ? kcal(macros.kcal) : "—"} kcal</strong>
        <span className="muted">
          {macros
            ? `P ${g1(macros.proteinG)} · H ${g1(macros.carbsG)} · G ${g1(macros.fatG)}`
            : "Introduce la cantidad"}
        </span>
        {mode === "servings" && valid && (
          <span className="muted">= {Math.round(effectiveGrams)} g</span>
        )}
      </div>

      {error && <p className="error">{error}</p>}
      <button type="button" className="wk-primary" disabled={!valid || busy} onClick={submit}>
        {busy ? "Guardando…" : "Añadir"}
      </button>
    </div>
  );
}
