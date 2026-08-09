import type { Session } from "@/lib/types";

function fmtDistance(meters: number): string {
  if (meters >= 1000) return `${(meters / 1000).toFixed(1)} km`;
  return `${Math.round(meters)} m`;
}

function fmtPace(durationMinutes: number, distanceMeters: number): string {
  const paceMinPerKm = durationMinutes / (distanceMeters / 1000);
  const totalSeconds = Math.round(paceMinPerKm * 60);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}'${String(seconds).padStart(2, "0")}" /km`;
}

export function ActivityStats({ session }: { session: Session }) {
  const duration = session.durationMinutes;
  const distance = session.distanceMeters ?? null;
  const details = session.details ?? {};
  const rpe = typeof details.rpe === "number" ? details.rpe : null;
  const avgHeartRate =
    typeof details.avgHeartRate === "number" ? details.avgHeartRate : null;

  return (
    <section className="stats">
      {duration != null && (
        <div className="stat-card">
          <span className="stat-label">Duración</span>
          <span className="stat-value">{duration} min</span>
        </div>
      )}
      {distance != null && (
        <div className="stat-card">
          <span className="stat-label">Distancia</span>
          <span className="stat-value">{fmtDistance(distance)}</span>
        </div>
      )}
      {distance != null && distance > 0 && duration != null && duration > 0 && (
        <div className="stat-card">
          <span className="stat-label">Ritmo medio</span>
          <span className="stat-value">{fmtPace(duration, distance)}</span>
        </div>
      )}
      {rpe != null && (
        <div className="stat-card">
          <span className="stat-label">Intensidad</span>
          <span className="stat-value">RPE {rpe}/10</span>
        </div>
      )}
      {avgHeartRate != null && (
        <div className="stat-card">
          <span className="stat-label">FC media</span>
          <span className="stat-value">{Math.round(avgHeartRate)} ppm</span>
        </div>
      )}
    </section>
  );
}
