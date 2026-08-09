import { SetRow } from "@/components/gym/SetRow";
import type { WorkoutExercise } from "@/lib/types";

type ExerciseGroup = { supersetGroupId: string | null; exercises: WorkoutExercise[] };

function groupExercises(exercises: WorkoutExercise[]): ExerciseGroup[] {
  const ordered = [...exercises].sort((a, b) => a.orderIndex - b.orderIndex);
  const groups: ExerciseGroup[] = [];
  for (const exercise of ordered) {
    const last = groups[groups.length - 1];
    const lastGroup = last?.exercises[last.exercises.length - 1].supersetGroupId ?? null;
    if (exercise.supersetGroupId != null && exercise.supersetGroupId === lastGroup) {
      last.exercises.push(exercise);
    } else {
      groups.push({ supersetGroupId: exercise.supersetGroupId, exercises: [exercise] });
    }
  }
  return groups;
}

function ExerciseBlock({ exercise }: { exercise: WorkoutExercise }) {
  const sets = [...exercise.sets].sort((a, b) => a.setNumber - b.setNumber);
  return (
    <div className="exercise-block">
      <div className="exercise-head">
        <h3>{exercise.name}</h3>
        <span className="exercise-volume muted">{Math.round(exercise.volumeKg)} kg</span>
      </div>
      <ul className="set-list">
        {sets.map((set) => (
          <SetRow key={set.id} set={set} />
        ))}
      </ul>
    </div>
  );
}

export function ExerciseRoutine({ exercises }: { exercises: WorkoutExercise[] }) {
  if (exercises.length === 0) {
    return (
      <section className="block">
        <h2>Rutina del entreno</h2>
        <p className="muted">Este entreno no tiene ejercicios registrados.</p>
      </section>
    );
  }

  return (
    <section className="block">
      <h2>Rutina del entreno</h2>
      {groupExercises(exercises).map((group, index) =>
        group.supersetGroupId != null ? (
          <div key={`${group.supersetGroupId}-${index}`} className="superset">
            <span className="superset-badge">Superserie</span>
            {group.exercises.map((exercise) => (
              <ExerciseBlock key={exercise.id} exercise={exercise} />
            ))}
          </div>
        ) : (
          <ExerciseBlock key={group.exercises[0].id} exercise={group.exercises[0]} />
        ),
      )}
    </section>
  );
}
