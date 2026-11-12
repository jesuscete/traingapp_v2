import type { ReactNode } from "react";

type Props = { value: ReactNode; label: string; delta?: number | null; deltaSuffix?: string };

export function StatTile({ value, label, delta, deltaSuffix = "%" }: Props) {
  return (
    <div className="ui-stat">
      <b className="ui-stat-value">{value}</b>
      <span className="ui-stat-label">{label}</span>
      {delta != null && (
        <span className={`ui-stat-delta ${delta >= 0 ? "up" : "down"}`}>
          {delta >= 0 ? "↑" : "↓"} {Math.abs(delta)}
          {deltaSuffix}
        </span>
      )}
    </div>
  );
}
