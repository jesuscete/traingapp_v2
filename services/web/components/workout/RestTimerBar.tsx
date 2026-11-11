"use client";

import { useRestTimer } from "@/lib/useRestTimer";
import type { RestState } from "@/lib/workout/types";

function mmss(ms: number): string {
  const total = Math.ceil(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

type Props = {
  rest: RestState | null;
  onExpire: () => void;
  onAdjust: (deltaMs: number) => void;
  onSkip: () => void;
};

export function RestTimerBar({ rest, onExpire, onAdjust, onSkip }: Props) {
  const remaining = useRestTimer(rest, onExpire);
  if (!rest || remaining === null) return null;
  const pct = Math.min(100, Math.max(0, (remaining / rest.total) * 100));
  return (
    <div className="rest-bar" role="timer" aria-live="off">
      <div className="rest-bar-fill" style={{ width: `${pct}%` }} />
      <button type="button" className="rest-btn" onClick={() => onAdjust(-15000)}>
        −15
      </button>
      <div className="rest-time">
        <span className="rest-label">Descanso</span>
        <strong>{mmss(remaining)}</strong>
      </div>
      <button type="button" className="rest-btn" onClick={() => onAdjust(15000)}>
        +15
      </button>
      <button type="button" className="rest-skip" onClick={onSkip}>
        Saltar
      </button>
    </div>
  );
}
