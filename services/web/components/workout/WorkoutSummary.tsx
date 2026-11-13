"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Sparkles, Trophy } from "lucide-react";

import { MuscleBody } from "@/components/MuscleChart";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { translateMuscleGroup } from "@/lib/labels";
import type { WeekFeedback } from "@/lib/types";
import type { WorkoutResult } from "@/lib/workout/types";

const TOP_MUSCLES = 4;

export function WorkoutSummary({
  token,
  result,
  onClose,
}: {
  token: string;
  result: WorkoutResult;
  onClose: () => void;
}) {
  const [feedback, setFeedback] = useState<WeekFeedback | null>(null);
  const saved = result.session !== null;

  useEffect(() => {
    // Sin conexión (entreno en cola) no hay semana que analizar: el resto del resumen basta.
    if (!saved) return;
    api.getWeekFeedback(token).then(setFeedback).catch(() => setFeedback(null));
  }, [token, saved]);

  const impacts = useMemo(
    () =>
      [...(result.session?.muscleImpacts ?? [])]
        .filter((m) => m.activation > 0)
        .sort((a, b) => b.activation - a.activation),
    [result.session?.muscleImpacts],
  );
  const bodyPoints = useMemo(() => {
    const max = Math.max(0.01, ...impacts.map((m) => m.activation));
    return impacts.map((m) => ({ muscleGroup: m.muscleGroup, value: m.activation / max }));
  }, [impacts]);

  return (
    <main className="dashboard wk-done">
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

      {feedback && (
        <section className="wk-feedback" aria-live="polite">
          <Sparkles size={20} strokeWidth={1.75} aria-hidden="true" />
          <div>
            <strong>{feedback.headline}</strong>
            <p>{feedback.message}</p>
          </div>
        </section>
      )}

      {bodyPoints.length > 0 && (
        <section className="block wk-done-body">
          <h2>Músculos trabajados</h2>
          <div className="wk-done-map">
            <MuscleBody points={bodyPoints} />
          </div>
          <div className="chips">
            {impacts.slice(0, TOP_MUSCLES).map((m) => (
              <span key={m.muscleGroup} className="chip">
                {translateMuscleGroup(m.muscleGroup)}
              </span>
            ))}
          </div>
        </section>
      )}

      {result.prs.length > 0 && (
        <section className="block">
          <h2>Récords</h2>
          <ul className="wk-prs">
            {result.prs.map((pr, i) => (
              <li key={i}>
                <Trophy size={16} strokeWidth={1.75} aria-hidden="true" /> {pr.exerciseName}:{" "}
                {pr.kind === "peso" ? "peso máx." : "1RM est."} <strong>{pr.value} kg</strong>
              </li>
            ))}
          </ul>
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
