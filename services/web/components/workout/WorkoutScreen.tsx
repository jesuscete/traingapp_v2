"use client";

import { useCallback, useState } from "react";

import { AddExerciseSheet } from "@/components/workout/AddExerciseSheet";
import { FinishDialog } from "@/components/workout/FinishDialog";
import { RestTimerBar } from "@/components/workout/RestTimerBar";
import { WorkoutExerciseCard } from "@/components/workout/WorkoutExerciseCard";
import { WorkoutHeader } from "@/components/workout/WorkoutHeader";
import type { CatalogExercise } from "@/lib/types";
import type { WorkoutUpdater } from "@/lib/useActiveWorkout";
import { useWakeLock } from "@/lib/useWakeLock";
import * as ops from "@/lib/workout/ops";
import { buildGymSessionPayload } from "@/lib/workout/payload";
import { detectPersonalRecords } from "@/lib/workout/records";
import { submitWorkout } from "@/lib/workout/sync";
import type { ActiveWorkout, WorkoutResult } from "@/lib/workout/types";

type Props = {
  token: string;
  workout: ActiveWorkout;
  update: WorkoutUpdater;
  onFinished: (result: WorkoutResult) => void;
  onDiscard: () => void;
};

type SheetState = { mode: "add" } | { mode: "substitute"; exerciseId: string } | null;

export function WorkoutScreen({ token, workout, update, onFinished, onDiscard }: Props) {
  const [sheet, setSheet] = useState<SheetState>(null);
  const [finishing, setFinishing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useWakeLock(true);

  const expireRest = useCallback(() => update(ops.skipRest), [update]);
  const adjustRest = useCallback((ms: number) => update((w) => ops.adjustRest(w, ms)), [update]);

  const stats = ops.workoutStats(workout);
  const discarded = workout.exercises.filter((ex) => !ex.sets.some((s) => s.done)).length;

  function handleSheetConfirm(list: CatalogExercise[]) {
    const current = sheet;
    setSheet(null);
    if (!current || list.length === 0) return;
    if (current.mode === "add") {
      update((w) => ops.addExercises(w, list.map((ex) => ops.exerciseFromCatalog(ex))));
    } else {
      update((w) => ops.substituteExercise(w, current.exerciseId, list[0]));
    }
  }

  async function confirmFinish() {
    setBusy(true);
    setError(null);
    const endedAt = Date.now();
    const payload = buildGymSessionPayload(workout, endedAt);
    if (!payload) {
      setBusy(false);
      setError("No hay series hechas que guardar.");
      return;
    }
    const prs = detectPersonalRecords(workout);
    try {
      const outcome = await submitWorkout(token, workout.id, payload);
      onFinished({
        session: outcome.status === "saved" ? outcome.session : null,
        title: payload.rawText,
        durationMin: payload.durationMinutes ?? 0,
        volumeKg: stats.volumeKg,
        setsCount: stats.setsDone,
        prs,
        queued: outcome.status === "queued",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el entreno");
      setBusy(false);
    }
  }

  return (
    <main className="dashboard wk-page">
      <WorkoutHeader
        workout={workout}
        onFinish={() => {
          setError(null);
          setFinishing(true);
        }}
      />

      {workout.exercises.length === 0 && (
        <p className="muted wk-empty">Añade tu primer ejercicio para empezar.</p>
      )}

      {workout.exercises.map((ex, i) => {
        const next = workout.exercises[i + 1];
        const inSuperset = ex.supersetGroupId !== null;
        return (
          <WorkoutExerciseCard
            key={ex.id}
            ex={ex}
            position={i}
            total={workout.exercises.length}
            inSuperset={inSuperset}
            linkedToNext={
              inSuperset && next !== undefined && next.supersetGroupId === ex.supersetGroupId
            }
            update={update}
            onSubstitute={() => setSheet({ mode: "substitute", exerciseId: ex.id })}
          />
        );
      })}

      <button type="button" className="wk-add-ex" onClick={() => setSheet({ mode: "add" })}>
        + Añadir ejercicio
      </button>

      <RestTimerBar
        rest={workout.rest}
        onExpire={expireRest}
        onAdjust={adjustRest}
        onSkip={expireRest}
      />

      {sheet && (
        <AddExerciseSheet
          token={token}
          title={sheet.mode === "add" ? "Añadir ejercicios" : "Sustituir ejercicio"}
          multiple={sheet.mode === "add"}
          alternativesFor={
            sheet.mode === "substitute"
              ? (workout.exercises.find((e) => e.id === sheet.exerciseId)?.exerciseId ?? null)
              : null
          }
          onClose={() => setSheet(null)}
          onConfirm={handleSheetConfirm}
        />
      )}

      {finishing && (
        <FinishDialog
          setsDone={stats.setsDone}
          setsPending={stats.setsTotal - stats.setsDone}
          exercisesDiscarded={discarded}
          busy={busy}
          error={error}
          onConfirm={() => void confirmFinish()}
          onCancel={() => setFinishing(false)}
          onDiscard={onDiscard}
        />
      )}
    </main>
  );
}
