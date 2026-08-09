import { formatDuration, formatKcal } from "@/lib/format";
import type { SummaryHighlights } from "@/lib/types";

export function HighlightsStats({
  highlights,
}: {
  highlights: SummaryHighlights;
}) {
  return (
    <div className="stats">
      <div className="stat-card">
        <span className="stat-label">Entrenos</span>
        <span className="stat-value">{highlights.totalSessions}</span>
      </div>
      <div className="stat-card">
        <span className="stat-label">Tiempo activo</span>
        <span className="stat-value">
          {formatDuration(highlights.totalDurationMinutes)}
        </span>
      </div>
      <div className="stat-card">
        <span className="stat-label">Volumen</span>
        <span className="stat-value">{Math.round(highlights.totalVolumeKg)} kg</span>
      </div>
      <div className="stat-card">
        <span className="stat-label">Calorías</span>
        <span className="stat-value">{formatKcal(highlights.totalKcal)}</span>
      </div>
    </div>
  );
}
