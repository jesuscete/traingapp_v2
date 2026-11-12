import { ClipboardList } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";

import { formatDuration } from "@/lib/format";
import { translateDiscipline } from "@/lib/labels";
import type { SessionSummary } from "@/lib/types";

export function RecentSessions({
  sessions,
  totalInPeriod,
  onSelect,
  selectedId,
}: {
  onSelect?: (id: string) => void;
  selectedId?: string | null;
  sessions: SessionSummary[];
  totalInPeriod: number;
}) {
  return (
    <section className="block">
      <h2>Entrenos recientes</h2>
      {sessions.length === 0 ? (
        <EmptyState icon={<ClipboardList size={28} strokeWidth={1.75} />} title="Sin entrenos en este periodo" text="Cambia el periodo o registra uno nuevo." action={{ label: "Empezar entreno", href: "/entrenar" }} />
      ) : (
        <ul className="recent-list">
          {sessions.map((session) => (
            <li key={session.id}>
              <Link
            className={`recent-link${selectedId === session.id ? " selected" : ""}`}
            href={`/entrenos/${session.id}`}
            onClick={onSelect ? (e) => { e.preventDefault(); onSelect(session.id); } : undefined}
          >
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
        <Link className="btn-secondary" href="/entrenar?tab=historial&view=todos">
          Ver todos los entrenos
        </Link>
      </p>
    </section>
  );
}
