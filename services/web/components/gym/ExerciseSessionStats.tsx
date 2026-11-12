import Link from "next/link";

import { translateSetType } from "@/lib/labels";
import { estimated1rm } from "@/lib/strength";
import type { WorkoutExercise } from "@/lib/types";

function best1rm(exercise: WorkoutExercise): number | null {
  let best: number | null = null;
  for (const set of exercise.sets) {
    if (set.isWarmup) continue;
    const entry = set.entries[0];
    if (!entry || entry.weight == null || !entry.reps) continue;
    const value = estimated1rm(entry.weight, entry.reps, entry.rpe);
    if (value == null) continue;
    if (best === null || value > best) best = value;
  }
  return best;
}

export function ExerciseSessionStats({ exercises }: { exercises: WorkoutExercise[] }) {
  const ordered = [...exercises].sort((a, b) => a.orderIndex - b.orderIndex);
  return (
    <section className="block">
      <h2>Series por ejercicio</h2>
      <div className="exercise-stats-grid">
        {ordered.map((exercise) => {
          const e1rm = best1rm(exercise);
          return (
            <div key={exercise.id} className="exercise-stats-placeholder">
              <h3>{exercise.name}</h3>
              <ol className="ex-hist-sets">
                {[...exercise.sets]
                  .sort((a, b) => a.setNumber - b.setNumber)
                  .map((set) => {
                    const entry = set.entries[0];
                    return (
                      <li key={set.id}>
                        <span className="muted">{set.setNumber}</span>
                        <span>
                          {entry?.weight != null ? `${entry.weight} kg` : "—"} × {entry?.reps ?? "—"}
                        </span>
                        <span className="muted">
                          {set.setType !== "normal" ? translateSetType(set.setType) : ""}
                          {entry?.rpe != null ? ` RPE ${entry.rpe}` : ""}
                        </span>
                      </li>
                    );
                  })}
              </ol>
              <p className="muted">
                Volumen {Math.round(exercise.volumeKg)} kg
                {e1rm != null ? ` · 1RM est. ${Math.round(e1rm * 10) / 10} kg` : ""}
              </p>
              {exercise.exerciseId && (
                <Link className="back-link" href={`/ejercicios/${exercise.exerciseId}`}>
                  Historial y progreso →
                </Link>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
