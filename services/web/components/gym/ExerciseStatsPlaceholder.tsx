import type { WorkoutExercise } from "@/lib/types";

export function ExerciseStatsPlaceholder({ exercises }: { exercises: WorkoutExercise[] }) {
  return (
    <section className="block">
      <h2>Estadísticas por ejercicio</h2>
      <div className="exercise-stats-grid">
        {exercises.map((exercise) => (
          <div key={exercise.id} className="exercise-stats-placeholder">
            <h3>{exercise.name}</h3>
            <p className="muted">Análisis por ejercicio (progresión) en una fase posterior.</p>
          </div>
        ))}
      </div>
    </section>
  );
}
