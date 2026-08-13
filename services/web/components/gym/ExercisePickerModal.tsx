"use client";

import { useEffect, useMemo, useState } from "react";

import { exerciseImageUrl } from "@/lib/format";
import { translateMuscleGroup } from "@/lib/labels";
import type { CatalogExercise } from "@/lib/types";

export type PickerSet = {
  setNumber: number;
  reps: number | null;
  weightKg: number | null;
};

export type PickerExercise = {
  exerciseId: string;
  name: string;
  sets: PickerSet[];
};

export const DEFAULT_SET_REPS = 10;

const MUSCLE_TAB_ORDER = [
  "chest",
  "back",
  "shoulders",
  "biceps",
  "triceps",
  "forearms",
  "core",
  "quadriceps",
  "hamstrings",
  "glutes",
  "calves",
  "neck",
];

function norm(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function numberOrNull(value: string): number | null {
  const parsed = Number(value);
  return value === "" || Number.isNaN(parsed) ? null : parsed;
}

function defaultSets(): PickerSet[] {
  return [
    { setNumber: 1, reps: DEFAULT_SET_REPS, weightKg: null },
    { setNumber: 2, reps: DEFAULT_SET_REPS, weightKg: null },
    { setNumber: 3, reps: DEFAULT_SET_REPS, weightKg: null },
  ];
}

type Props = {
  catalog: CatalogExercise[];
  initial?: PickerExercise[];
  lockedIds?: string[];
  title?: string;
  onSave: (exercises: PickerExercise[]) => void;
  onCancel: () => void;
};

export function ExercisePickerModal({
  catalog,
  initial = [],
  lockedIds = [],
  title = "Añadir ejercicio",
  onSave,
  onCancel,
}: Props) {
  const [tab, setTab] = useState("all");
  const [search, setSearch] = useState("");
  const [draft, setDraft] = useState<PickerExercise[]>(initial);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onCancel]);

  const muscleTabs = useMemo(() => {
    const counts = new Map<string, number>();
    for (const exercise of catalog) {
      for (const code of Object.keys(exercise.muscleMap)) {
        counts.set(code, (counts.get(code) ?? 0) + 1);
      }
    }
    return [...counts.entries()]
      .filter(([code]) => code !== "other")
      .sort(
        (a, b) => MUSCLE_TAB_ORDER.indexOf(a[0]) - MUSCLE_TAB_ORDER.indexOf(b[0]),
      );
  }, [catalog]);

  const results = useMemo(() => {
    const q = norm(search.trim());
    if (q !== "") {
      return catalog.filter((item) => norm(item.name).includes(q));
    }
    if (tab === "all") return catalog;
    return catalog.filter((item) => (item.muscleMap[tab] ?? 0) > 0);
  }, [catalog, search, tab]);

  function toggleExercise(exercise: CatalogExercise) {
    setDraft((prev) =>
      prev.some((item) => item.exerciseId === exercise.id)
        ? prev.filter((item) => item.exerciseId !== exercise.id)
        : [
            ...prev,
            { exerciseId: exercise.id, name: exercise.name, sets: defaultSets() },
          ],
    );
  }

  function removeExercise(exerciseId: string) {
    setDraft((prev) => prev.filter((item) => item.exerciseId !== exerciseId));
  }

  function addSet(exerciseId: string) {
    setDraft((prev) =>
      prev.map((item) =>
        item.exerciseId === exerciseId
          ? {
              ...item,
              sets: [
                ...item.sets,
                { setNumber: item.sets.length + 1, reps: DEFAULT_SET_REPS, weightKg: null },
              ],
            }
          : item,
      ),
    );
  }

  function removeSet(exerciseId: string) {
    setDraft((prev) =>
      prev.map((item) => {
        if (item.exerciseId !== exerciseId || item.sets.length <= 1) return item;
        const sets = item.sets
          .filter((_, index) => index !== item.sets.length - 1)
          .map((workoutSet, index) => ({ ...workoutSet, setNumber: index + 1 }));
        return { ...item, sets };
      }),
    );
  }

  function updateSet(exerciseId: string, setIndex: number, patch: Partial<PickerSet>) {
    setDraft((prev) =>
      prev.map((item) =>
        item.exerciseId === exerciseId
          ? {
              ...item,
              sets: item.sets.map((workoutSet, index) =>
                index === setIndex ? { ...workoutSet, ...patch } : workoutSet,
              ),
            }
          : item,
      ),
    );
  }

  return (
    <div className="picker-overlay" onClick={onCancel}>
      <div className="picker-modal" onClick={(event) => event.stopPropagation()}>
        <div className="picker-header">
          <h2>{title}</h2>
          <button type="button" className="link" onClick={onCancel}>
            Cerrar
          </button>
        </div>

        <input
          type="search"
          className="search-input"
          placeholder="Buscar ejercicio por nombre (ej: press)..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          autoFocus
        />

        <div className="picker-tabs chips">
          <button
            type="button"
            className={`chip chip-toggle${tab === "all" ? " on" : ""}`}
            onClick={() => setTab("all")}
          >
            Todos
          </button>
          {muscleTabs.map(([code]) => (
            <button
              key={code}
              type="button"
              className={`chip chip-toggle${tab === code ? " on" : ""}`}
              onClick={() => setTab(code)}
            >
              {translateMuscleGroup(code)}
            </button>
          ))}
        </div>

        <div className="picker-body">
          <div className="picker-results">
            {results.length === 0 && <p className="muted">Sin resultados.</p>}
            {results.map((exercise) => {
              const image = exerciseImageUrl(exercise.images[0]);
              const added = draft.some((item) => item.exerciseId === exercise.id);
              const locked = lockedIds.includes(exercise.id);
              return (
                <button
                  key={exercise.id}
                  type="button"
                  disabled={locked}
                  className={`picker-card${added ? " added" : ""}`}
                  onClick={() => toggleExercise(exercise)}
                >
                  {image ? (
                    <img className="exercise-thumb" src={image} alt="" loading="lazy" />
                  ) : null}
                  <span>{exercise.name}</span>
                  {locked ? (
                    <em className="picker-locked">En sesión</em>
                  ) : added ? (
                    <em className="picker-added">Añadido</em>
                  ) : null}
                </button>
              );
            })}
          </div>

          <div className="picker-draft">
            <h3>En el plan ({draft.length})</h3>
            {draft.length === 0 && (
              <p className="muted">Toca un ejercicio para añadirlo.</p>
            )}
            {draft.map((item) => (
              <div key={item.exerciseId} className="picker-exercise">
                <div className="picker-exercise-header">
                  <strong>{item.name}</strong>
                  <button
                    type="button"
                    className="link"
                    onClick={() => removeExercise(item.exerciseId)}
                  >
                    Quitar
                  </button>
                </div>
                <table className="plain routine-sets">
                  <thead>
                    <tr>
                      <th>Serie</th>
                      <th>Reps</th>
                      <th>Peso (kg)</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {item.sets.map((workoutSet, setIndex) => (
                      <tr key={workoutSet.setNumber}>
                        <td>{workoutSet.setNumber}</td>
                        <td>
                          <input
                            className="cell"
                            type="number"
                            min="1"
                            placeholder="10"
                            value={workoutSet.reps ?? ""}
                            onChange={(event) =>
                              updateSet(item.exerciseId, setIndex, {
                                reps: numberOrNull(event.target.value),
                              })
                            }
                          />
                        </td>
                        <td>
                          <input
                            className="cell"
                            type="number"
                            min="0"
                            step="0.5"
                            placeholder="—"
                            value={workoutSet.weightKg ?? ""}
                            onChange={(event) =>
                              updateSet(item.exerciseId, setIndex, {
                                weightKg: numberOrNull(event.target.value),
                              })
                            }
                          />
                        </td>
                        <td>
                          <button
                            type="button"
                            className="link"
                            disabled={item.sets.length <= 1}
                            onClick={() => removeSet(item.exerciseId)}
                          >
                            −
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button type="button" className="link" onClick={() => addSet(item.exerciseId)}>
                  + Serie
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="picker-actions chat-actions">
          <button type="button" className="secondary" onClick={onCancel}>
            Cancelar
          </button>
          <button type="button" disabled={draft.length === 0} onClick={() => onSave(draft)}>
            Guardar ({draft.length})
          </button>
        </div>
      </div>
    </div>
  );
}
