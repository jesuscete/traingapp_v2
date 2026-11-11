"use client";

import Link from "next/link";

import { formatDuration } from "@/lib/format";
import { translateMuscleGroup } from "@/lib/labels";
import type { WorkoutResult } from "@/lib/workout/types";

export function WorkoutSummary({
  result,
  onClose,
}: {
  result: WorkoutResult;
  onClose: () => void;
}) {
  const impacts = [...(result.session?.muscleImpacts ?? [])]
    .filter((m) => m.activation > 0)
    .sort((a, b) => b.activation - a.activation);
  return (
    <main className="dashboard">
      <section className="welcome">
        <h2>{result.queued ? "Entreno guardado en el móvil" : "¡Entreno completado!"}</h2>
        <p className="subtitle">{result.title}</p>
      </section>

      {result.queued && (
        <p className="wk-warn" role="status">
          No hay conexión con el servidor. Se enviará automáticamente cuando vuelva la conexión.
        </p>
      )}

      <div className="wk-stats wk-summary-stats">
        <div>
          <span className="muted">Duración</span>
          <strong>{formatDuration(result.durationMin)}</strong>
        </div>
        <div>
          <span className="muted">Volumen</span>
          <strong>{Math.round(result.volumeKg)} kg</strong>
        </div>
        <div>
          <span className="muted">Series</span>
          <strong>{result.setsCount}</strong>
        </div>
      </div>

      <section className="block">
        <h2>Récords</h2>
        {result.prs.length === 0 ? (
          <p className="muted">Sin récords nuevos esta vez.</p>
        ) : (
          <ul className="wk-prs">
            {result.prs.map((pr, i) => (
              <li key={i}>
                <span aria-hidden="true">🏆</span> PR · {pr.exerciseName}:{" "}
                {pr.kind === "peso" ? "peso máx." : "1RM est."} <strong>{pr.value} kg</strong>
              </li>
            ))}
          </ul>
        )}
      </section>

      {impacts.length > 0 && (
        <section className="block">
          <h2>Músculos trabajados</h2>
          <div className="chips">
            {impacts.map((m) => (
              <span key={m.muscleGroup} className="chip">
                {translateMuscleGroup(m.muscleGroup)} · {Math.round(m.activation * 100)}%
              </span>
            ))}
          </div>
        </section>
      )}

      <div className="chat-actions">
        {result.session && (
          <Link className="btn-secondary" href={`/entrenos/${result.session.id}`}>
            Ver detalle
          </Link>
        )}
        <button type="button" className="wk-primary" onClick={onClose}>
          Listo
        </button>
      </div>
    </main>
  );
}
