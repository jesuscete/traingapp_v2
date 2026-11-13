"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { Sheet } from "@/components/nutrition/Sheet";
import { errMsg, parseNum } from "@/lib/nutrition";
import type { ActivityMode, GoalType } from "@/lib/types";

const GOALS: { key: GoalType; label: string; help: string }[] = [
  { key: "perder", label: "Perder grasa", help: "Déficit moderado y sostenido a un ritmo semanal fijo." },
  { key: "mantener", label: "Mantener", help: "Comes tu mantenimiento: ni subes ni bajas." },
  { key: "ganar", label: "Ganar", help: "Superávit ligero para ganar masa con poca grasa." },
  {
    key: "corte",
    label: "Corte (peso objetivo y fecha)",
    help: "Llegar a un peso concreto en una fecha (p. ej. pesaje). El déficit se calcula solo y se limita para que sea seguro.",
  },
];

// "registro": solo el día a día; el deporte lo ponen tus entrenos registrados.
const ACTIVITY_DAILY: { value: number; label: string }[] = [
  { value: 1.2, label: "Sentado" },
  { value: 1.3, label: "Algo de pie" },
  { value: 1.45, label: "De pie / andando" },
  { value: 1.6, label: "Trabajo físico" },
];
// "estimado": incluye el deporte semanal porque no se suman los entrenos.
const ACTIVITY_WITH_SPORT: { value: number; label: string }[] = [
  { value: 1.4, label: "1-2 entrenos/sem" },
  { value: 1.55, label: "3-4 entrenos/sem" },
  { value: 1.7, label: "5-6 entrenos/sem" },
  { value: 1.9, label: "Doble sesión" },
];

type Props = { token: string; onClose: () => void; onSaved: () => void };

export function GoalSheet({ token, onClose, onSaved }: Props) {
  const [loaded, setLoaded] = useState(false);
  const [goal, setGoal] = useState<GoalType>("mantener");
  const [targetWeight, setTargetWeight] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [rate, setRate] = useState("");
  const [protein, setProtein] = useState("2.0");
  const [activity, setActivity] = useState("1.3");
  const [mode, setMode] = useState<ActivityMode>("registro");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getNutritionGoal(token)
      .then((g) => {
        if (cancelled) return;
        setGoal(g.goal);
        setTargetWeight(g.targetWeightKg != null ? String(g.targetWeightKg) : "");
        setTargetDate(g.targetDate ?? "");
        setRate(g.rateKgWeek != null ? String(g.rateKgWeek) : "");
        setProtein(String(g.proteinGPerKg));
        setActivity(String(g.activityFactor));
        setMode(g.activityMode ?? "registro");
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const tw = parseNum(targetWeight);
    const rt = parseNum(rate);
    const pr = parseNum(protein);
    const ac = parseNum(activity);
    if (goal === "corte" && !(Number.isFinite(tw) && tw > 20 && tw < 400))
      return setError("El corte necesita un peso objetivo.");
    if (!Number.isFinite(pr) || pr < 0.8 || pr > 3.5) return setError("Proteína: entre 0,8 y 3,5 g/kg.");
    if (!Number.isFinite(ac) || ac < 1.1 || ac > 2.0) return setError("Factor de actividad: entre 1,1 y 2,0.");
    if (Number.isFinite(rt) && (rt < 0 || rt > 2)) return setError("Ritmo: entre 0 y 2 kg/semana.");
    setBusy(true);
    setError(null);
    try {
      await api.saveNutritionGoal(token, {
        goal,
        targetWeightKg: goal === "corte" || goal === "perder" ? (Number.isFinite(tw) ? tw : null) : null,
        targetDate: goal === "corte" && targetDate ? targetDate : null,
        rateKgWeek: goal !== "corte" && goal !== "mantener" && Number.isFinite(rt) ? rt : null,
        proteinGPerKg: pr,
        activityFactor: ac,
        activityMode: mode,
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(errMsg(err, "No se pudo guardar el objetivo"));
      setBusy(false);
    }
  }

  const current = GOALS.find((g) => g.key === goal);

  return (
    <Sheet title="Objetivo" onClose={onClose}>
      {!loaded ? (
        <Skeleton height={120} />
      ) : (
        <form className="nu-form" onSubmit={save}>
          <label className="nu-field">
            <span>Tipo de objetivo</span>
            <select value={goal} onChange={(e) => setGoal(e.target.value as GoalType)}>
              {GOALS.map((g) => (
                <option key={g.key} value={g.key}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
          {current && <p className="muted nu-note">{current.help}</p>}

          {(goal === "corte" || goal === "perder") && (
            <label className="nu-field">
              <span>Peso objetivo (kg){goal === "corte" ? "" : " (opcional)"}</span>
              <input type="text" inputMode="decimal" value={targetWeight} onChange={(e) => setTargetWeight(e.target.value)} />
            </label>
          )}
          {goal === "corte" && (
            <label className="nu-field">
              <span>Fecha objetivo</span>
              <input type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
            </label>
          )}
          {(goal === "perder" || goal === "ganar") && (
            <label className="nu-field">
              <span>Ritmo (kg/semana, opcional)</span>
              <input type="text" inputMode="decimal" placeholder="0.5" value={rate} onChange={(e) => setRate(e.target.value)} />
            </label>
          )}

          <label className="nu-field">
            <span>Proteína (g por kg de peso)</span>
            <input type="text" inputMode="decimal" value={protein} onChange={(e) => setProtein(e.target.value)} />
          </label>
          <p className="muted nu-note">
            2,0 g/kg es un buen punto de partida; en déficit, 2,2-2,4 ayuda a conservar músculo. Rango 0,8-3,5.
          </p>

          <div className="nu-field">
            <span>¿Cómo calculo tu gasto?</span>
            <div className="nu-chips">
              <button
                type="button"
                className={`nu-chip${mode === "registro" ? " active" : ""}`}
                onClick={() => {
                  setMode("registro");
                  setActivity("1.3");
                }}
              >
                Según lo que registro (recomendado)
              </button>
              <button
                type="button"
                className={`nu-chip${mode === "estimado" ? " active" : ""}`}
                onClick={() => {
                  setMode("estimado");
                  setActivity("1.55");
                }}
              >
                Estimado (no registro siempre)
              </button>
            </div>
          </div>
          <p className="muted nu-note">
            {mode === "registro"
              ? "Cada día se suman las kcal reales de los entrenos que registras: un día de boxeo sube tu objetivo más que uno de gimnasio y un día de descanso lo baja. Es lo más preciso."
              : "Usamos una media fija que ya incluye tu deporte y no sumamos los entrenos registrados. Útil si se te olvida registrar, pero menos fino: registrar tus entrenos hace que la app acierte más."}
          </p>

          <label className="nu-field">
            <span>{mode === "registro" ? "Actividad del día a día (sin entrenar)" : "Actividad total (con deporte)"}</span>
            <input type="text" inputMode="decimal" value={activity} onChange={(e) => setActivity(e.target.value)} />
          </label>
          <div className="nu-chips">
            {(mode === "registro" ? ACTIVITY_DAILY : ACTIVITY_WITH_SPORT).map((a) => (
              <button
                key={a.value}
                type="button"
                className={`nu-chip${Number(activity) === a.value ? " active" : ""}`}
                onClick={() => setActivity(String(a.value))}
              >
                {a.label} {String(a.value).replace(".", ",")}
              </button>
            ))}
          </div>
          <p className="muted nu-note">
            {mode === "registro"
              ? "Solo trabajo y pasos: no cuentes el deporte aquí o se sumaría dos veces."
              : "Elige según cuántas veces entrenas a la semana."}
          </p>

          {error && <p className="error">{error}</p>}
          <button type="submit" className="wk-primary" disabled={busy}>
            {busy ? "Guardando…" : "Guardar objetivo"}
          </button>
        </form>
      )}
    </Sheet>
  );
}
