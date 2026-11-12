"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { errMsg, g1, itemMacros, kcal, parseNum, sourceLabel } from "@/lib/nutrition";
import type { MealName, ProposedItem } from "@/lib/types";
import { X } from "lucide-react";

type Props = { token: string; day: string; meal: MealName; onSaved: () => void };

type Row = { item: ProposedItem; gramsText: string };

export function FreeTextTab({ token, day, meal, onSaved }: Props) {
  const [text, setText] = useState("");
  const [rows, setRows] = useState<Row[] | null>(null);
  const [unresolved, setUnresolved] = useState<string[]>([]);
  const [fallback, setFallback] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function calculate() {
    if (text.trim().length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.parseMeal(token, text.trim());
      setRows(res.items.map((item) => ({ item, gramsText: String(Math.round(item.grams * 10) / 10) })));
      setUnresolved(res.unresolved);
      setFallback(res.source === "fallback");
    } catch (err) {
      setError(errMsg(err, "No se pudo calcular la comida"));
    } finally {
      setLoading(false);
    }
  }

  const items: ProposedItem[] = (rows ?? []).map((r) => {
    const g = parseNum(r.gramsText);
    return { ...r.item, grams: Number.isFinite(g) && g > 0 ? g : r.item.grams };
  });
  const allValid = (rows ?? []).every((r) => {
    const g = parseNum(r.gramsText);
    return Number.isFinite(g) && g > 0 && g <= 5000;
  });
  const total = items.reduce((acc, it) => acc + itemMacros(it).kcal, 0);

  async function save() {
    if (!rows || rows.length === 0 || !allValid) return;
    setSaving(true);
    setError(null);
    try {
      await api.saveMealBatch(token, { eatenOn: day, meal, items });
      onSaved();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar"));
      setSaving(false);
    }
  }

  if (rows === null) {
    return (
      <div className="nu-form">
        <label className="nu-field">
          <span>Describe lo que has comido</span>
          <textarea
            rows={4}
            placeholder="Ej.: 2 tostadas con crema de cacahuete y un café con leche"
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
          />
        </label>
        <p className="muted nu-note">
          La IA estima gramos y valores; revisa antes de guardar. Para máxima precisión, pesa y usa Buscar.
        </p>
        {error && <p className="error">{error}</p>}
        <button
          type="button"
          className="wk-primary"
          disabled={loading || text.trim().length < 2}
          onClick={calculate}
        >
          {loading ? "Calculando…" : "Calcular"}
        </button>
        {loading && <p className="muted nu-pulse">Calculando… puede tardar unos segundos.</p>}
      </div>
    );
  }

  return (
    <div className="nu-form">
      {fallback && (
        <p className="nu-warn">La IA no estaba disponible: resultado aproximado, revísalo con cuidado.</p>
      )}
      {unresolved.length > 0 && (
        <p className="nu-warn">
          No he podido calcular: {unresolved.join(", ")}. Añádelos con Buscar o Rápido.
        </p>
      )}
      {rows.length === 0 && <p className="muted">No hay alimentos en la propuesta.</p>}
      <ul className="nu-list">
        {rows.map((row, i) => {
          const m = itemMacros(items[i]);
          return (
            <li key={`${row.item.name}-${i}`} className="nu-prop">
              <div className="nu-prop-head">
                <strong>{row.item.name}</strong>
                <span className={`nu-badge nu-src-${row.item.source}`}>{sourceLabel(row.item.source)}</span>
              </div>
              <div className="nu-prop-row">
                <input
                  type="text"
                  inputMode="decimal"
                  aria-label={`Gramos de ${row.item.name}`}
                  value={row.gramsText}
                  onChange={(e) =>
                    setRows((list) =>
                      (list ?? []).map((r, idx) => (idx === i ? { ...r, gramsText: e.target.value } : r)),
                    )
                  }
                />
                <span className="muted">g</span>
                <span className="nu-prop-kcal">
                  {kcal(m.kcal)} kcal
                  <small className="muted">
                    {" "}
                    P {g1(m.proteinG)} · H {g1(m.carbsG)} · G {g1(m.fatG)}
                  </small>
                </span>
                <button
                  type="button"
                  className="secondary nu-icon-btn"
                  aria-label={`Quitar ${row.item.name}`}
                  onClick={() => setRows((list) => (list ?? []).filter((_, idx) => idx !== i))}
                >
                  <X size={18} strokeWidth={1.75} aria-hidden="true" />
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      <p className="nu-total">
        Total: <strong>{kcal(total)} kcal</strong> <span className="muted">(estimado)</span>
      </p>
      {error && <p className="error">{error}</p>}
      <div className="nu-actions">
        <button type="button" className="secondary" onClick={() => setRows(null)} disabled={saving}>
          Volver a escribir
        </button>
        <button type="button" disabled={saving || rows.length === 0 || !allValid} onClick={save}>
          {saving ? "Guardando…" : "Guardar"}
        </button>
      </div>
    </div>
  );
}
