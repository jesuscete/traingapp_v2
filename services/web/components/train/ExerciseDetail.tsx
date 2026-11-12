"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { BodyMap } from "@/components/BodyMap";
import { ExerciseAnimation } from "@/components/gym/ExerciseAnimation";
import { ExerciseHistoryView } from "@/components/gym/ExerciseHistoryView";
import { FavoriteButton } from "@/components/gym/FavoriteButton";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import {
  exerciseDisplayName,
  exerciseInstructions,
  primaryMuscles,
  secondaryMuscles,
} from "@/lib/exerciseSearch";
import { translateMuscleGroup } from "@/lib/labels";
import type { ExerciseHistory } from "@/lib/types";
import { useCatalog } from "@/lib/useCatalog";
import { useToken } from "@/lib/useToken";

export function ExerciseDetail({ id, embedded = false, onDeleted }: { id: string; embedded?: boolean; onDeleted?: () => void }) {
  const params = { id };
  const token = useToken();
  const router = useRouter();
  const { catalog, loading, error, toggleFavorite, removeExercise } = useCatalog(token);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [history, setHistory] = useState<ExerciseHistory | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(true);

  const exercise = useMemo(
    () => catalog.find((ex) => ex.id === params.id) ?? null,
    [catalog, params.id],
  );

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setHistoryLoading(true);
    api
      .getExerciseHistory(token, params.id, 30)
      .then((h) => {
        if (!cancelled) {
          setHistory(h);
          setHistoryError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setHistoryError(err instanceof Error ? err.message : "No se pudo cargar el historial");
      })
      .finally(() => {
        if (!cancelled) setHistoryLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, params.id]);

  async function deleteExercise() {
    if (!token || !exercise) return;
    if (!window.confirm(`¿Eliminar el ejercicio "${exerciseDisplayName(exercise)}"?`)) return;
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteCustomExercise(token, exercise.id);
      removeExercise(exercise.id);
      if (onDeleted) onDeleted();
      else router.replace("/entrenar?tab=ejercicios");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "No se pudo eliminar el ejercicio");
      setDeleting(false);
    }
  }

  const instructions = exercise ? exerciseInstructions(exercise) : [];
  const primary = exercise ? primaryMuscles(exercise) : [];
  const secondary = exercise ? secondaryMuscles(exercise) : [];

  return (
    <div className="detail-pane">
      {!embedded && (
        <p>
          <Link className="back-link" href="/entrenar?tab=ejercicios">
            ← Ejercicios
          </Link>
        </p>
      )}

      {loading && !exercise && <div className="detail-skeleton"><Skeleton height={32} width="60%" /><Skeleton height={220} /></div>}
      {error && <p className="error">{error}</p>}
      {!loading && !error && !exercise && <p className="muted">Ejercicio no encontrado.</p>}

      {exercise && (
        <>
          <section className="ex-detail-head">
            <div>
              <h2>
                {exerciseDisplayName(exercise)}
                {exercise.isCustom && <span className="ex-badge">Propio</span>}
              </h2>
              {exercise.details?.nameEs && exercise.details.nameEs !== exercise.name && (
                <p className="muted">{exercise.name}</p>
              )}
              <p className="muted">
                {[exercise.details?.equipment, exercise.details?.level, exercise.details?.category]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <FavoriteButton
              active={exercise.isFavorite}
              onToggle={() => void toggleFavorite(exercise.id)}
            />
          </section>

          <ExerciseAnimation urls={exercise.imageUrls} alt={exerciseDisplayName(exercise)} />

          <section className="block">
            <h2>Músculos</h2>
            <div className="chips">
              {primary.map((m) => (
                <span key={m} className="chip ex-chip-primary">
                  {translateMuscleGroup(m)}
                </span>
              ))}
              {secondary.map((m) => (
                <span key={m} className="chip">
                  {translateMuscleGroup(m)}
                </span>
              ))}
            </div>
            <BodyMap
              showLegend={false}
              points={Object.entries(exercise.muscleMap)
                .filter(([, v]) => v > 0)
                .map(([muscleGroup, value]) => ({ muscleGroup, value }))}
            />
          </section>

          {instructions.length > 0 && (
            <section className="block">
              <h2>Instrucciones</h2>
              <ol className="ex-instructions">
                {instructions.map((step, i) => (
                  <li key={i}>{step}</li>
                ))}
              </ol>
            </section>
          )}

          {historyLoading && <Skeleton height={140} />}
          {historyError && <p className="error">{historyError}</p>}
          {history && <ExerciseHistoryView history={history} />}

          {exercise.isCustom && (
            <section className="block ce-danger">
              {deleteError && <p className="error">{deleteError}</p>}
              <button
                type="button"
                className="wk-danger"
                disabled={deleting}
                onClick={() => void deleteExercise()}
              >
                {deleting ? "Eliminando…" : "Eliminar ejercicio"}
              </button>
            </section>
          )}
        </>
      )}
    </div>
  );
}
