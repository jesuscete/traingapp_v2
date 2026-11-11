import {
  BLOCK_TYPE_LABELS,
  CLIMBING_STYLE_LABELS,
  combatTotals,
  formatDistance,
  formatPaceText,
  formatRoundTime,
} from "@/lib/metrics";
import type { SessionMetrics } from "@/lib/types";

type Props = {
  metrics: SessionMetrics;
  discipline: string;
  durationMinutes: number | null;
};

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function trim(n: number): string {
  return String(Number(n.toFixed(1)));
}

export function MetricsView({ metrics, discipline, durationMinutes }: Props) {
  if (metrics.kind === "combat") {
    const totals = combatTotals(metrics.blocks);
    return (
      <section className="block">
        <h2>Bloques</h2>
        <div className="stats">
          {totals.rounds > 0 && <Stat label="Rounds totales" value={String(totals.rounds)} />}
          <Stat label="Minutos totales" value={`${trim(totals.minutes)} min`} />
        </div>
        <ul className="m3-list">
          {metrics.blocks.map((b, i) => (
            <li key={i}>
              <strong>{BLOCK_TYPE_LABELS[b.type] ?? b.type}</strong>
              <span>
                {b.rounds != null
                  ? `${b.rounds} × ${formatRoundTime(b.roundSeconds ?? 180)}`
                  : `${trim(b.minutes ?? 0)} min`}
                {b.strikes != null ? ` · ${b.strikes} golpes` : ""}
              </span>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (metrics.kind === "endurance") {
    const pace = formatPaceText(discipline, metrics.distanceMeters, durationMinutes);
    const hasAny =
      metrics.distanceMeters != null ||
      metrics.avgHeartRate != null ||
      metrics.maxHeartRate != null ||
      metrics.elevationGainM != null;
    if (!hasAny) return null;
    return (
      <section className="block">
        <h2>Resistencia</h2>
        <div className="stats">
          {metrics.distanceMeters != null && (
            <Stat label="Distancia" value={formatDistance(metrics.distanceMeters)} />
          )}
          {pace && <Stat label="Ritmo" value={pace} />}
          {metrics.avgHeartRate != null && (
            <Stat label="FC media" value={`${metrics.avgHeartRate} ppm`} />
          )}
          {metrics.maxHeartRate != null && (
            <Stat label="FC máxima" value={`${metrics.maxHeartRate} ppm`} />
          )}
          {metrics.elevationGainM != null && (
            <Stat label="Desnivel +" value={`${Math.round(metrics.elevationGainM)} m`} />
          )}
        </div>
      </section>
    );
  }

  if (metrics.kind === "climbing") {
    const sent = metrics.routes.filter((r) => r.sent).length;
    return (
      <section className="block">
        <h2>Escalada · {CLIMBING_STYLE_LABELS[metrics.style] ?? metrics.style}</h2>
        <p className="muted">
          {sent} de {metrics.routes.length} encadenadas
        </p>
        <ul className="m3-list">
          {metrics.routes.map((r, i) => (
            <li key={i}>
              <strong>{r.grade}</strong>
              <span>
                {r.attempts != null ? `${r.attempts} int. · ` : ""}
                <span className={r.sent ? "m3-ok" : "m3-fail"}>
                  {r.sent ? "Encadenada" : "No encadenada"}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  if (!metrics.notes) return null;
  return (
    <section className="block">
      <h2>Notas de la actividad</h2>
      <p>{metrics.notes}</p>
    </section>
  );
}
