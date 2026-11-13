"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { errMsg, g1, parseNum, shortDate } from "@/lib/nutrition";
import type { WeightSeries } from "@/lib/types";

const W = 320;
const H = 120;
const PAD = { l: 34, r: 8, t: 10, b: 18 };

function Trend({ points }: { points: WeightSeries["points"] }) {
  if (points.length < 2) return null;
  const vals = points.map((p) => p.weightKg);
  let lo = Math.min(...vals);
  let hi = Math.max(...vals);
  if (hi - lo < 1) {
    const mid = (hi + lo) / 2;
    lo = mid - 0.5;
    hi = mid + 0.5;
  }
  const pw = W - PAD.l - PAD.r;
  const ph = H - PAD.t - PAD.b;
  const x = (i: number) => PAD.l + (i / (points.length - 1)) * pw;
  const y = (v: number) => PAD.t + ((hi - v) / (hi - lo)) * ph;
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.weightKg).toFixed(1)}`).join(" ");
  const last = points.length - 1;
  return (
    <svg className="nu-trend" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Tendencia de peso">
      <line x1={PAD.l} x2={W - PAD.r} y1={y(hi)} y2={y(hi)} className="lc-grid" />
      <line x1={PAD.l} x2={W - PAD.r} y1={y(lo)} y2={y(lo)} className="lc-grid" />
      <text x={PAD.l - 4} y={y(hi) + 3} textAnchor="end" className="lc-tick">
        {g1(hi)}
      </text>
      <text x={PAD.l - 4} y={y(lo) + 3} textAnchor="end" className="lc-tick">
        {g1(lo)}
      </text>
      <path d={d} fill="none" className="nu-trend-line" />
      {points.map((p, i) => (
        <circle key={p.measuredOn} cx={x(i)} cy={y(p.weightKg)} r={i === last ? 4 : 2.5} className="nu-trend-dot" />
      ))}
      <text x={PAD.l} y={H - 4} className="lc-tick">
        {shortDate(points[0].measuredOn)}
      </text>
      <text x={W - PAD.r} y={H - 4} textAnchor="end" className="lc-tick">
        {shortDate(points[last].measuredOn)}
      </text>
    </svg>
  );
}

type Props = { token: string; day: string; onChanged: () => void };

/** Vacío -> undefined (no medido); fuera de rango o no numérico -> null (error). */
function optionalPct(text: string, min: number, max: number): number | undefined | null {
  if (text.trim() === "") return undefined;
  const value = parseNum(text);
  return Number.isFinite(value) && value >= min && value <= max ? value : null;
}

export function WeightCard({ token, day, onChanged }: Props) {
  const [series, setSeries] = useState<WeightSeries | null>(null);
  const [text, setText] = useState("");
  const [fatText, setFatText] = useState("");
  const [muscleText, setMuscleText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSeries(await api.getWeight(token, 90));
    } catch (err) {
      setError(errMsg(err, "No se pudo cargar el peso"));
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const dayPoint = series?.points.find((p) => p.measuredOn === day);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const kg = parseNum(text);
    if (!Number.isFinite(kg) || kg <= 20 || kg >= 400) {
      setError("Introduce un peso válido (kg).");
      return;
    }
    const fat = optionalPct(fatText, 2, 70);
    const muscle = optionalPct(muscleText, 10, 80);
    if (fat === null || muscle === null) {
      setError("Revisa los porcentajes: grasa entre 2 y 70 %, músculo entre 10 y 80 %.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setSeries(
        await api.addWeight(token, { measuredOn: day, weightKg: kg, bodyFatPct: fat, musclePct: muscle }),
      );
      setText("");
      setFatText("");
      setMuscleText("");
      onChanged();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar el peso"));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api.deleteWeight(token, day);
      await load();
      onChanged();
    } catch (err) {
      setError(errMsg(err, "No se pudo borrar"));
    } finally {
      setBusy(false);
    }
  }

  const change = series?.changeWeekKg ?? null;

  return (
    <section className="block nu-weight">
      <h2>Peso</h2>
      <div className="nu-weight-stats">
        <div>
          <span className="muted">Último</span>
          <strong>{series?.latestKg != null ? `${g1(series.latestKg)} kg` : "—"}</strong>
        </div>
        <div>
          <span className="muted">Media 7 d</span>
          <strong>{series?.average7dKg != null ? `${g1(series.average7dKg)} kg` : "—"}</strong>
        </div>
        <div>
          <span className="muted">Cambio semanal</span>
          <strong className={change === null ? "" : change < 0 ? "nu-down" : change > 0 ? "nu-up" : ""}>
            {change !== null ? `${change > 0 ? "+" : ""}${g1(change)} kg` : "—"}
          </strong>
        </div>
      </div>
      {(series?.latestBodyFatPct != null || series?.latestMusclePct != null) && (
        <div className="nu-weight-stats">
          <div>
            <span className="muted">% grasa</span>
            <strong>{series?.latestBodyFatPct != null ? `${g1(series.latestBodyFatPct)} %` : "—"}</strong>
          </div>
          <div>
            <span className="muted">% músculo</span>
            <strong>{series?.latestMusclePct != null ? `${g1(series.latestMusclePct)} %` : "—"}</strong>
          </div>
        </div>
      )}
      {series && <Trend points={series.points.slice(-30)} />}
      <form className="nu-weight-form" onSubmit={save}>
        <label className="nu-field nu-weight-kg">
          <span>Peso (kg)</span>
          <input
            type="text"
            inputMode="decimal"
            placeholder={dayPoint ? `${g1(dayPoint.weightKg)} (registrado)` : "Peso de hoy"}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </label>
        <label className="nu-field">
          <span>% grasa</span>
          <input
            type="text"
            inputMode="decimal"
            placeholder={dayPoint?.bodyFatPct != null ? g1(dayPoint.bodyFatPct) : "Opcional"}
            value={fatText}
            onChange={(e) => setFatText(e.target.value)}
          />
        </label>
        <label className="nu-field">
          <span>% músculo</span>
          <input
            type="text"
            inputMode="decimal"
            placeholder={dayPoint?.musclePct != null ? g1(dayPoint.musclePct) : "Opcional"}
            value={muscleText}
            onChange={(e) => setMuscleText(e.target.value)}
          />
        </label>
        <button type="submit" disabled={busy || text.trim() === ""}>
          {dayPoint ? "Actualizar" : "Guardar"}
        </button>
      </form>
      <p className="muted nu-note">% de grasa y músculo: solo si tu báscula los mide.</p>
      {dayPoint && (
        <button type="button" className="secondary nu-add-link" disabled={busy} onClick={remove}>
          Borrar el peso de este día
        </button>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
