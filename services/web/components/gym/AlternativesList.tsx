"use client";

import { useEffect, useState } from "react";

import { ExerciseThumb } from "@/components/gym/ExerciseThumb";
import { api } from "@/lib/api";
import { getCatalog } from "@/lib/catalogCache";
import { EQUIPMENT_LABELS } from "@/components/account/EquipmentCard";
import type { CatalogExercise, EquipmentCode, ExerciseAlternative } from "@/lib/types";

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
  const [withoutOwn, setWithoutOwn] = useState(false);
  const [sourceEquipment, setSourceEquipment] = useState<string | null>(null);

  useEffect(() => {
    setWithoutOwn(false);
  }, [exerciseId]);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setItems(null);
    setFailed(false);
    const without = withoutOwn && sourceEquipment ? [sourceEquipment] : [];
    Promise.all([api.getExerciseAlternatives(token, exerciseId, 8, without), getCatalog(token)])
      .then(([alts, list]) => {
        if (cancelled) return;
        setCatalog(new Map(list.map((ex) => [ex.id, ex])));
        setSourceEquipment(list.find((ex) => ex.id === exerciseId)?.equipment ?? null);
        setItems(alts);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [token, exerciseId, withoutOwn, sourceEquipment]);

  if (failed) return null;

  const equipmentLabel =
    sourceEquipment && sourceEquipment !== "body only"
      ? (EQUIPMENT_LABELS[sourceEquipment as EquipmentCode] ?? sourceEquipment)
      : null;

  return (
    <section className="alt-section">
      <div className="m10-alt-head">
        <h4 className="alt-title">Alternativas recomendadas</h4>
        {equipmentLabel && (
          <button
            type="button"
            className={`chip chip-toggle${withoutOwn ? " on" : ""}`}
            aria-pressed={withoutOwn}
            onClick={() => setWithoutOwn((v) => !v)}
          >
            No tengo {equipmentLabel.toLowerCase()}
          </button>
        )}
      </div>
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
                  {alt.reason && <small className="muted m10-alt-reason">{alt.reason}</small>}
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
