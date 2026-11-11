"use client";

import { useElapsed } from "@/lib/useRestTimer";
import { workoutStats } from "@/lib/workout/ops";
import type { ActiveWorkout } from "@/lib/workout/types";

function clock(totalSeconds: number): string {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

export function WorkoutHeader({
  workout,
  onFinish,
}: {
  workout: ActiveWorkout;
  onFinish: () => void;
}) {
  const elapsed = useElapsed(workout.startedAt);
  const stats = workoutStats(workout);
  return (
    <header className="wk-header">
      <div className="wk-header-title">
        <h2>{workout.title || "Entreno libre"}</h2>
        <button type="button" className="wk-finish" onClick={onFinish}>
          Terminar
        </button>
      </div>
      <div className="wk-stats">
        <div>
          <span className="muted">Tiempo</span>
          <strong>{clock(elapsed)}</strong>
        </div>
        <div>
          <span className="muted">Volumen</span>
          <strong>{Math.round(stats.volumeKg)} kg</strong>
        </div>
        <div>
          <span className="muted">Series</span>
          <strong>
            {stats.setsDone}/{stats.setsTotal}
          </strong>
        </div>
      </div>
    </header>
  );
}
