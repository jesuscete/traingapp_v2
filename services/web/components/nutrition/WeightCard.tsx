"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { BodyChart } from "@/components/nutrition/BodyChart";
import { bodyTrend, MIN_POINTS } from "@/lib/bodyTrend";
import { errMsg, g1, parseNum, todayISO } from "@/lib/nutrition";
import type { NutritionGoal, WeightSeries } from "@/lib/types";

type Props = { token: string; day: string; onChanged: () => void };

/** Vacío -> undefined (no medido); fuera de rango o no numérico -> null (error). */
function optionalPct(text: string, min: number, max: number): number | undefined | null {
  if (text.trim() === "") return undefined;
  const value = parseNum(text);
  return Number.isFinite(value) && value >= min && value <= max ? value : null;
}

export function WeightCard({ token, day, onChanged }: Props) {
  const [series, setSeries] = useState<WeightSeries | null>(null);
  const [goal, setGoal] = useState<NutritionGoal | null>(null);
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

  useEffect(() => {
    api.getNutritionGoal(token).then(setGoal).catch(() => setGoal(null));
  }, [token]);

  const trend = useMemo(
    () => (series && series.points.length >= MIN_POINTS ? bodyTrend(series.points, goal, todayISO()) : null),
    [series, goal],
  );

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
      {series &&
        (series.points.length >= MIN_POINTS ? (
          <>
            <BodyChart points={series.points} />
            {trend && (
              <div className="bc-analysis">
                <p>{trend.summary}</p>
                {trend.goal && <p className={`bc-goal tone-${trend.goal.tone}`}>{trend.goal.text}</p>}
              </div>
            )}
          </>
        ) : (
          <p className="muted bc-empty">
            Registra {MIN_POINTS - series.points.length} {MIN_POINTS - series.points.length === 1 ? "peso más" : "pesos más"} para
            ver tu evolución (peso, % graso y % músculo) y la tendencia.
          </p>
        ))}
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
