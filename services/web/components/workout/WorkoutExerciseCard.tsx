"use client";

import Link from "next/link";
import { useState } from "react";

import { ExerciseThumb } from "@/components/gym/ExerciseThumb";
import { WorkoutSetRow } from "@/components/workout/WorkoutSetRow";
import type { WorkoutUpdater } from "@/lib/useActiveWorkout";
import { primeAudio } from "@/lib/alert";
import * as ops from "@/lib/workout/ops";
import type { WorkoutExercise } from "@/lib/workout/types";

type Props = {
  ex: WorkoutExercise;
  position: number;
  total: number;
  inSuperset: boolean;
  linkedToNext: boolean;
  update: WorkoutUpdater;
  onSubstitute: () => void;
};

export function WorkoutExerciseCard({
  ex,
  position,
  total,
  inSuperset,
  linkedToNext,
  update,
  onSubstitute,
}: Props) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [noteOpen, setNoteOpen] = useState(ex.note !== "");
  const doneCount = ex.sets.filter((s) => s.done).length;

  function closeAnd(fn: () => void) {
    setMenuOpen(false);
    fn();
  }

  return (
    <article className={`wk-card${inSuperset ? " superset" : ""}`}>
      <header className="wk-card-head">
        <ExerciseThumb src={ex.imageUrl} size={44} />
        <div className="wk-card-title">
          {ex.exerciseId ? (
            <Link href={`/ejercicios/${ex.exerciseId}`} className="wk-card-name">
              {ex.name}
            </Link>
          ) : (
            <span className="wk-card-name">{ex.name}</span>
          )}
          <span className="muted wk-card-sub">
            {inSuperset && <span className="wk-ss-tag">Superserie</span>}
            {doneCount}/{ex.sets.length} series · descanso {ex.restSeconds}s
          </span>
        </div>
        <button
          type="button"
          className="wk-menu-btn"
          aria-label="Opciones del ejercicio"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((v) => !v)}
        >
          ⋯
        </button>
        {menuOpen && (
          <>
            <div className="wk-menu-backdrop" onClick={() => setMenuOpen(false)} aria-hidden="true" />
            <div className="wk-menu" role="menu">
              <button type="button" role="menuitem" onClick={() => closeAnd(onSubstitute)}>
                Sustituir ejercicio
              </button>
              <button
                type="button"
                role="menuitem"
                disabled={position === 0}
                onClick={() => closeAnd(() => update((w) => ops.moveExercise(w, ex.id, -1)))}
              >
                Mover arriba
              </button>
              <button
                type="button"
                role="menuitem"
                disabled={position === total - 1}
                onClick={() => closeAnd(() => update((w) => ops.moveExercise(w, ex.id, 1)))}
              >
                Mover abajo
              </button>
              <button
                type="button"
                role="menuitem"
                disabled={position === total - 1}
                onClick={() => closeAnd(() => update((w) => ops.toggleSupersetWithNext(w, ex.id)))}
              >
                {linkedToNext ? "Separar del siguiente" : "Superserie con el siguiente"}
              </button>
              <button type="button" role="menuitem" onClick={() => closeAnd(() => setNoteOpen(true))}>
                Nota
              </button>
              <div className="wk-menu-rest">
                <span>Descanso</span>
                <button
                  type="button"
                  aria-label="Menos 15 segundos"
                  onClick={() => update((w) => ops.setRestSeconds(w, ex.id, ex.restSeconds - 15))}
                >
                  −15
                </button>
                <strong>{ex.restSeconds}s</strong>
                <button
                  type="button"
                  aria-label="Más 15 segundos"
                  onClick={() => update((w) => ops.setRestSeconds(w, ex.id, ex.restSeconds + 15))}
                >
                  +15
                </button>
              </div>
              <button
                type="button"
                role="menuitem"
                className="danger"
                onClick={() => closeAnd(() => update((w) => ops.removeExercise(w, ex.id)))}
              >
                Eliminar ejercicio
              </button>
            </div>
          </>
        )}
      </header>

      {noteOpen && (
        <textarea
          className="wk-note"
          rows={2}
          placeholder="Nota del ejercicio (ajuste de máquina, sensaciones…)"
          value={ex.note}
          onChange={(e) => update((w) => ops.setNote(w, ex.id, e.target.value))}
        />
      )}

      <div className="wk-grid-head" aria-hidden="true">
        <span>Serie</span>
        <span>Anterior</span>
        <span>kg</span>
        <span>Reps</span>
        <span>RPE</span>
        <span />
      </div>
      {ex.sets.map((s, i) => (
        <WorkoutSetRow
          key={s.id}
          ex={ex}
          index={i}
          onPatch={(patch) => update((w) => ops.patchSet(w, ex.id, s.id, patch))}
          onCycleType={() => update((w) => ops.cycleSetType(w, ex.id, s.id))}
          onToggleDone={() => {
            primeAudio();
            update((w) => ops.toggleDone(w, ex.id, s.id));
          }}
          onDelete={() => update((w) => ops.deleteSet(w, ex.id, s.id))}
        />
      ))}
      <button
        type="button"
        className="wk-add-set"
        onClick={() => update((w) => ops.addSet(w, ex.id))}
      >
        + Añadir serie
      </button>
    </article>
  );
}
