"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api";
import { applyHistory } from "@/lib/workout/ops";
import { loadActiveWorkout, saveActiveWorkout } from "@/lib/workout/storage";
import type { ActiveWorkout } from "@/lib/workout/types";

export type WorkoutUpdater = (fn: (w: ActiveWorkout) => ActiveWorkout) => void;

/**
 * Entreno activo en cliente: se restaura de localStorage y se persiste en cada cambio.
 * Además carga (una vez por ejercicio) el historial para "Anterior" y récords.
 */
export function useActiveWorkout(token: string | null) {
  const [workout, setWorkout] = useState<ActiveWorkout | null>(null);
  const [ready, setReady] = useState(false);
  const fetching = useRef(new Set<string>());

  useEffect(() => {
    setWorkout(loadActiveWorkout());
    setReady(true);
  }, []);

  useEffect(() => {
    if (ready) saveActiveWorkout(workout);
  }, [workout, ready]);

  useEffect(() => {
    if (!token || !workout) return;
    for (const ex of workout.exercises) {
      if (ex.history !== "pending" || fetching.current.has(ex.id)) continue;
      const exId = ex.id;
      if (!ex.exerciseId) {
        setWorkout((w) => (w ? applyHistory(w, exId, null) : w));
        continue;
      }
      fetching.current.add(exId);
      api
        .getExerciseHistory(token, ex.exerciseId, 1)
        .then((history) => setWorkout((w) => (w ? applyHistory(w, exId, history) : w)))
        .catch(() => setWorkout((w) => (w ? applyHistory(w, exId, null) : w)))
        .finally(() => fetching.current.delete(exId));
    }
  }, [token, workout]);

  const update: WorkoutUpdater = useCallback((fn) => {
    setWorkout((w) => (w ? fn(w) : w));
  }, []);

  const start = useCallback((w: ActiveWorkout) => setWorkout(w), []);
  const clear = useCallback(() => setWorkout(null), []);

  return { workout, ready, update, start, clear };
}
