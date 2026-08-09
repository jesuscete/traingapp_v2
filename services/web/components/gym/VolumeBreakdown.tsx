import type { GymSession } from "@/lib/types";

export function VolumeBreakdown({ session }: { session: GymSession }) {
  const total = session.summary?.totalVolume ?? session.volumeKg;
  const exercises = [...session.workoutExercises].sort((a, b) => a.orderIndex - b.orderIndex);

  return (
    <section className="block">
      <h2>Volumen de carga total</h2>
      <div className="stats">
        <div className="stat-card">
          <span className="stat-label">Volumen total (sin calentamientos)</span>
          <span className="stat-value">{Math.round(total)} kg</span>
        </div>
      </div>
      {exercises.length > 0 && (
        <table className="plain">
          <thead>
            <tr>
              <th>Ejercicio</th>
              <th>Volumen</th>
              <th>Aporte</th>
            </tr>
          </thead>
          <tbody>
            {exercises.map((exercise) => (
              <tr key={exercise.id}>
                <td>{exercise.name}</td>
                <td>{Math.round(exercise.volumeKg)} kg</td>
                <td>{total > 0 ? `${Math.round((exercise.volumeKg / total) * 100)}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
