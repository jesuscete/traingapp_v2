import type { SportTarget, TargetStatus } from "@/lib/types";

const STATUS_LABEL: Record<TargetStatus, string> = {
  missing: "Falta",
  low: "Bajo",
  ok: "Bien",
  high: "Alto",
};

function fmt(value: number, percent: boolean): string {
  if (percent) return `${Math.round(value * 100)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(1);
}

function pct(value: number, max: number): number {
  return max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
}

export function TargetBars({
  items,
  percent = false,
}: {
  items: SportTarget[];
  percent?: boolean;
}) {
  if (items.length === 0) return <p className="muted">Sin datos.</p>;
  return (
    <div className="m4-targets">
      {items.map((t) => {
        const top = t.high ?? t.low;
        const max = Math.max(t.value, top, t.low) * 1.25 || 1;
        const target =
          t.high != null
            ? `${fmt(t.low, percent)}–${fmt(t.high, percent)}`
            : `mín. ${fmt(t.low, percent)}`;
        return (
          <div key={t.key} className="m4-target">
            <div className="m4-target-head">
              <span className="m4-target-label">{t.label}</span>
              <span className={`m4-status m4-status-${t.status}`}>{STATUS_LABEL[t.status]}</span>
            </div>
            <div
              className="m4-track"
              role="img"
              aria-label={`${t.label}: ${fmt(t.value, percent)}, objetivo ${target}`}
            >
              {t.high != null ? (
                <div
                  className="m4-band"
                  style={{
                    left: `${pct(t.low, max)}%`,
                    width: `${pct(t.high - t.low, max)}%`,
                  }}
                />
              ) : (
                <div className="m4-mark" style={{ left: `${pct(t.low, max)}%` }} />
              )}
              <div
                className={`m4-fill m4-fill-${t.status}`}
                style={{ width: `${pct(t.value, max)}%` }}
              />
            </div>
            <div className="m4-target-foot muted">
              <span>
                {fmt(t.value, percent)}
                {percent ? "" : " series/sem"}
              </span>
              <span>Objetivo {target}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
