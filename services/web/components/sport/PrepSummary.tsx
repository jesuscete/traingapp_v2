import type { SportAnalysis } from "@/lib/types";

export function MiniRing({ score }: { score: number }) {
  const r = 30;
  const c = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, score));
  const color = clamped >= 70 ? "var(--accent2)" : clamped >= 40 ? "#f5b942" : "#ef4444";
  return (
    <div className="hm-ring" role="img" aria-label={`Puntuación ${Math.round(clamped)} de 100`}>
      <svg width="76" height="76" viewBox="0 0 76 76" aria-hidden="true">
        <circle cx="38" cy="38" r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
        <circle
          cx="38"
          cy="38"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          strokeDasharray={`${(clamped / 100) * c} ${c}`}
          transform="rotate(-90 38 38)"
        />
      </svg>
      <div className="hm-ring-label">
        <b>{Math.round(clamped)}</b>
        <span className="muted">/100</span>
      </div>
    </div>
  );
}

export function PrepSummary({ data, maxGaps = 2 }: { data: SportAnalysis; maxGaps?: number }) {
  const order = { alta: 0, media: 1, baja: 2 } as const;
  const gaps = [...data.gaps].sort((a, b) => order[a.severity] - order[b.severity]).slice(0, maxGaps);
  return (
    <div className="hm-prep">
      <MiniRing score={data.score} />
      <div className="hm-prep-gaps">
        {gaps.length === 0 ? (
          <p className="muted">Sin carencias importantes. Buen trabajo.</p>
        ) : (
          gaps.map((g) => <p key={g.code}>{g.message}</p>)
        )}
      </div>
    </div>
  );
}
