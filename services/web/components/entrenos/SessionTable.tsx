import Link from "next/link";

import { formatDuration } from "@/lib/format";
import { translateDiscipline } from "@/lib/labels";
import type { SessionSummary } from "@/lib/types";

export function SessionTable({
  sessions,
  onSelect,
  selectedId,
}: {
  sessions: SessionSummary[];
  onSelect?: (id: string) => void;
  selectedId?: string | null;
}) {
  return (
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
  );
}
