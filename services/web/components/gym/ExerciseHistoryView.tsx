"use client";

import { LineChart } from "@/components/LineChart";
import { translateSetType } from "@/lib/labels";
import type { ExerciseHistory } from "@/lib/types";

function kg(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${Math.round(value * 10) / 10} kg`;
}

function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-ES", { day: "numeric", month: "short" });
}

export function ExerciseHistoryView({ history }: { history: ExerciseHistory }) {
  const { records, progress, sessions } = history;
  const points = progress.filter((p) => p.bestE1rmKg != null);
  const values = points.map((p) => p.bestE1rmKg as number);
  const lo = values.length ? Math.floor(Math.min(...values) * 0.9) : 0;
  const hi = values.length ? Math.ceil(Math.max(...values) * 1.05) : 100;

  return (
    <>
      <section className="block">
        <h2>Récords</h2>
        <div className="ex-records">
          <div className="ex-record">
            <span className="muted">Peso máx.</span>
            <strong>{kg(records.maxWeightKg)}</strong>
          </div>
          <div className="ex-record">
            <span className="muted">1RM estimado</span>
            <strong>{kg(records.bestE1rmKg)}</strong>
          </div>
          <div className="ex-record">
            <span className="muted">Más reps</span>
            <strong>{records.maxReps ?? "—"}</strong>
          </div>
          <div className="ex-record">
            <span className="muted">Mejor volumen (serie)</span>
            <strong>{kg(records.bestSetVolumeKg)}</strong>
          </div>
        </div>
      </section>

      <section className="block">
        <h2>Progreso (1RM estimado)</h2>
        {points.length < 2 ? (
          <p className="muted">Se necesitan al menos 2 sesiones para ver la evolución.</p>
        ) : (
          <LineChart
            labels={points.map((p) => shortDate(p.performedAt))}
            series={[
              {
                name: "1RM",
                color: "var(--accent)",
                points: points.map((p) => p.bestE1rmKg),
              },
            ]}
            min={lo}
            max={hi}
          />
        )}
      </section>

      <section className="block">
        <h2>Historial</h2>
        {sessions.length === 0 ? (
          <p className="muted">Aún no has hecho este ejercicio.</p>
        ) : (
          <ul className="ex-hist">
            {sessions.map((s) => (
              <li key={s.sessionId} className="ex-hist-item">
                <h3>{new Date(s.performedAt).toLocaleDateString("es-ES", {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })}</h3>
                <ol className="ex-hist-sets">
                  {[...s.sets]
                    .sort((a, b) => a.setNumber - b.setNumber)
                    .map((set) => (
                      <li key={set.setNumber}>
                        <span className="muted">{set.setNumber}</span>
                        <span>
                          {set.weightKg != null ? `${set.weightKg} kg` : "—"} × {set.reps ?? "—"}
                        </span>
                        <span className="muted">
                          {set.isWarmup || set.setType !== "normal"
                            ? translateSetType(set.setType)
                            : ""}
                          {set.rpe != null ? ` RPE ${set.rpe}` : ""}
                        </span>
                      </li>
                    ))}
                </ol>
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  );
}
