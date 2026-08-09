import Link from "next/link";

import { formatDuration } from "@/lib/format";
import { translateDiscipline } from "@/lib/labels";
import type { SessionSummary } from "@/lib/types";

export function RecentSessions({
  sessions,
  totalInPeriod,
}: {
  sessions: SessionSummary[];
  totalInPeriod: number;
}) {
  return (
    <section className="block">
      <h2>Entrenos recientes</h2>
      {sessions.length === 0 ? (
        <p className="muted">Sin entrenos en este periodo.</p>
      ) : (
        <ul className="recent-list">
          {sessions.map((session) => (
            <li key={session.id}>
              <Link className="recent-link" href={`/entrenos/${session.id}`}>
                <span className="recent-date">
                  {new Date(session.performedAt).toLocaleDateString()}
                </span>
                <span className="chip">
                  {translateDiscipline(session.discipline)}
                </span>
                <span className="recent-title">{session.rawText}</span>
                <span className="recent-metric">
                  {session.volumeKg > 0
                    ? `${Math.round(session.volumeKg)} kg`
                    : formatDuration(session.durationMinutes)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {totalInPeriod > sessions.length && (
        <p className="muted">
          …y {totalInPeriod - sessions.length} más en este periodo.
        </p>
      )}
      <p className="block">
        <Link className="btn-secondary" href="/entrenos?view=todos">
          Ver todos los entrenos
        </Link>
      </p>
    </section>
  );
}
