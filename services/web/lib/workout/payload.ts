import type { GymExerciseIn, GymSessionIn, GymSetIn, GymSetType } from "@/lib/types";
import { parseNum } from "@/lib/workout/ops";
import type { ActiveWorkout, WorkoutExercise } from "@/lib/workout/types";

const SET_TYPE_API: Record<string, GymSetType> = {
  normal: "normal",
  calentamiento: "calentamiento",
  dropset: "dropset",
  al_fallo: "al_fallo",
};

function buildExercise(ex: WorkoutExercise, orderIndex: number): GymExerciseIn | null {
  const done = ex.sets.filter((s) => s.done);
  if (done.length === 0) return null;
  const sets: GymSetIn[] = done.map((s, i) => {
    const reps = parseNum(s.reps);
    const rpe = parseNum(s.rpe);
    return {
      setNumber: i + 1,
      setType: SET_TYPE_API[s.type] ?? "normal",
      restSeconds: ex.restSeconds,
      isWarmup: s.type === "calentamiento",
      entries: [
        {
          entryOrder: 0,
          reps: reps != null ? Math.round(reps) : null,
          weight: parseNum(s.weight),
          weightUnit: "kg",
          rpe: rpe != null ? Math.min(10, Math.max(1, Math.round(rpe))) : null,
          side: "both",
        },
      ],
    };
  });
  return {
    exerciseId: ex.exerciseId,
    name: ex.name,
    orderIndex,
    supersetGroupId: ex.supersetGroupId,
    sets,
  };
}

/** Solo series hechas; descarta ejercicios sin ninguna. Devuelve null si no queda nada. */
export function buildGymSessionPayload(
  w: ActiveWorkout,
  endedAt = Date.now(),
): GymSessionIn | null {
  const exercises: GymExerciseIn[] = [];
  const kept: WorkoutExercise[] = [];
  for (const ex of w.exercises) {
    const built = buildExercise(ex, exercises.length);
    if (built) {
      exercises.push(built);
      kept.push(ex);
    }
  }
  if (exercises.length === 0) return null;
  const counts = new Map<string, number>();
  for (const ex of exercises) {
    if (ex.supersetGroupId) {
      counts.set(ex.supersetGroupId, (counts.get(ex.supersetGroupId) ?? 0) + 1);
    }
  }
  for (const ex of exercises) {
    if (ex.supersetGroupId && (counts.get(ex.supersetGroupId) ?? 0) < 2) {
      ex.supersetGroupId = null;
    }
  }
  const notes = kept
    .filter((ex) => ex.note.trim())
    .map((ex) => `${ex.name}: ${ex.note.trim()}`)
    .join("\n");
  return {
    clientId: w.id,
    rawText: w.title.trim() || "Entreno libre",
    performedAt: new Date(w.startedAt).toISOString(),
    startTime: new Date(w.startedAt).toISOString(),
    endTime: new Date(endedAt).toISOString(),
    durationMinutes: Math.max(1, Math.round((endedAt - w.startedAt) / 60000)),
    note: notes || null,
    routineDayId: w.routineDayId,
    exercises,
  };
}
