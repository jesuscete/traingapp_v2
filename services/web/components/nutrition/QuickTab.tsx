"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { errMsg, parseNum } from "@/lib/nutrition";
import type { MealName } from "@/lib/types";

type Props = { token: string; day: string; meal: MealName; onSaved: () => void };

function opt(value: string): number | undefined {
  const n = parseNum(value);
  return Number.isFinite(n) ? n : undefined;
}

export function QuickTab({ token, day, meal, onSaved }: Props) {
  const [name, setName] = useState("");
  const [kcalText, setKcalText] = useState("");
  const [p, setP] = useState("");
  const [c, setC] = useState("");
  const [f, setF] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const k = parseNum(kcalText);
    if (!name.trim() || !Number.isFinite(k) || k < 0 || k > 10000) {
      setError("Indica un nombre y las kcal (0-10000).");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.addMealEntry(token, {
        eatenOn: day,
        meal,
        name: name.trim(),
        kcal: k,
        proteinG: opt(p),
        carbsG: opt(c),
        fatG: opt(f),
      });
      onSaved();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar"));
      setBusy(false);
    }
  }

  return (
    <form className="nu-form" onSubmit={submit}>
      <p className="muted nu-note">Añadido rápido: cuenta como estimado.</p>
      <label className="nu-field">
        <span>Nombre</span>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} />
      </label>
      <label className="nu-field">
        <span>kcal</span>
        <input type="text" inputMode="decimal" value={kcalText} onChange={(e) => setKcalText(e.target.value)} />
      </label>
      <div className="nu-grid3">
        <label className="nu-field">
          <span>P (g)</span>
          <input type="text" inputMode="decimal" value={p} onChange={(e) => setP(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>H (g)</span>
          <input type="text" inputMode="decimal" value={c} onChange={(e) => setC(e.target.value)} />
        </label>
        <label className="nu-field">
          <span>G (g)</span>
          <input type="text" inputMode="decimal" value={f} onChange={(e) => setF(e.target.value)} />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <button type="submit" className="wk-primary" disabled={busy}>
        {busy ? "Guardando…" : "Añadir"}
      </button>
    </form>
  );
}
