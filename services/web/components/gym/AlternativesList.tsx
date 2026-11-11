"use client";

import { useEffect, useState } from "react";

import { ExerciseThumb } from "@/components/gym/ExerciseThumb";
import { api } from "@/lib/api";
import { getCatalog } from "@/lib/catalogCache";
import type { CatalogExercise, ExerciseAlternative } from "@/lib/types";

type Props = {
  token: string | null;
  exerciseId: string;
  onPick: (exercise: CatalogExercise) => void;
};

/** "Alternativas recomendadas" para sustituir un ejercicio. */
export function AlternativesList({ token, exerciseId, onPick }: Props) {
  const [items, setItems] = useState<ExerciseAlternative[] | null>(null);
  const [catalog, setCatalog] = useState<Map<string, CatalogExercise>>(new Map());
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setItems(null);
    setFailed(false);
    Promise.all([api.getExerciseAlternatives(token, exerciseId, 8), getCatalog(token)])
      .then(([alts, list]) => {
        if (cancelled) return;
        setCatalog(new Map(list.map((ex) => [ex.id, ex])));
        setItems(alts);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [token, exerciseId]);

  if (failed) return null;

  return (
    <section className="alt-section">
      <h4 className="alt-title">Alternativas recomendadas</h4>
      {items === null ? (
        <p className="muted alt-empty">Buscando alternativas…</p>
      ) : items.length === 0 ? (
        <p className="muted alt-empty">No hay alternativas similares.</p>
      ) : (
        <div className="alt-list">
          {items.map((alt) => {
            const full = catalog.get(alt.exerciseId);
            return (
              <button
                key={alt.exerciseId}
                type="button"
                className="alt-row"
                disabled={!full}
                onClick={() => full && onPick(full)}
              >
                <ExerciseThumb src={alt.imageUrl} size={44} />
                <span className="alt-name">
                  {alt.name}
                  {alt.isCustom && <em className="alt-custom">Propio</em>}
                </span>
                <span className="alt-sim">{Math.round(alt.similarity * 100)}%</span>
              </button>
            );
          })}
        </div>
      )}
      <h4 className="alt-title">Toda la biblioteca</h4>
    </section>
  );
}
