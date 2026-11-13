"use client";

import { useState } from "react";

import { Sheet } from "@/components/nutrition/Sheet";
import { api } from "@/lib/api";
import { DAY_MEAL, dayLabel, errMsg, parseNum } from "@/lib/nutrition";
import type { MealEntry } from "@/lib/types";

type Props = {
  token: string;
  day: string;
  /** Registros de día completo ya guardados: se sustituyen al guardar. */
  existing: MealEntry[];
  onClose: () => void;
  onSaved: () => void;
};

function initial(value: number | undefined): string {
  return value !== undefined && value > 0 ? String(Math.round(value)) : "";
}

function opt(value: string): number | undefined {
  const n = parseNum(value);
  return Number.isFinite(n) && n >= 0 ? n : undefined;
}

/** Registro agregado de todo el día (kcal y macros traídos de otra app). */
export function DayLogSheet({ token, day, existing, onClose, onSaved }: Props) {
  const prev = existing[0];
  const [kcalText, setKcalText] = useState(initial(prev?.kcal));
  const [p, setP] = useState(initial(prev?.proteinG));
  const [c, setC] = useState(initial(prev?.carbsG));
  const [f, setF] = useState(initial(prev?.fatG));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const k = parseNum(kcalText);
    if (!Number.isFinite(k) || k <= 0 || k > 10000) {
      setError("Indica las kcal del día (1-10000).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      // Primero se guarda el nuevo y luego se borran los anteriores: si falla, no se pierde nada.
      await api.addMealEntry(token, {
        eatenOn: day,
        meal: DAY_MEAL.key,
        name: "Registro del día",
        kcal: k,
        proteinG: opt(p),
        carbsG: opt(c),
        fatG: opt(f),
      });
      for (const entry of existing) await api.deleteMealEntry(token, entry.id);
      onSaved();
      onClose();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar"));
      setBusy(false);
    }
  }

  return (
    <Sheet title={`Registrar día · ${dayLabel(day)}`} onClose={onClose} compact>
      <form className="nu-form" onSubmit={submit}>
        <p className="muted nu-note">
          Totales del día de otra app. Cuenta como estimado
          {existing.length > 0 ? " y sustituye al registro del día que ya tenías." : "."}
        </p>
        <label className="nu-field">
          <span>kcal</span>
          <input
            type="text"
            inputMode="decimal"
            autoFocus
            value={kcalText}
            onChange={(e) => setKcalText(e.target.value)}
          />
        </label>
        <div className="nu-grid3">
          <label className="nu-field">
            <span>Proteína (g)</span>
            <input type="text" inputMode="decimal" value={p} onChange={(e) => setP(e.target.value)} />
          </label>
          <label className="nu-field">
            <span>Hidratos (g)</span>
            <input type="text" inputMode="decimal" value={c} onChange={(e) => setC(e.target.value)} />
          </label>
          <label className="nu-field">
            <span>Grasa (g)</span>
            <input type="text" inputMode="decimal" value={f} onChange={(e) => setF(e.target.value)} />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="wk-primary" disabled={busy}>
          {busy ? "Guardando…" : "Guardar día"}
        </button>
      </form>
    </Sheet>
  );
}
