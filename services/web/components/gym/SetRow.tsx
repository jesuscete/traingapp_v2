import { translateSetType } from "@/lib/labels";
import type { SetEntry, WorkoutSet } from "@/lib/types";

const LB_TO_KG = 0.45359237;

function fmtWeight(weightKg: number | null, unit: string): string {
  if (weightKg == null) return "—";
  const shown = unit === "lb" ? weightKg / LB_TO_KG : weightKg;
  return `${Math.round(shown * 100) / 100} ${unit}`;
}

function fmtEntry(entry: SetEntry): string {
  if (entry.reps != null && entry.reps >= 1) return `${entry.reps} reps`;
  if (entry.durationSeconds != null) return `${entry.durationSeconds}s`;
  return "—";
}

function sideLabel(side: string): string | null {
  if (side === "left") return "Izq";
  if (side === "right") return "Der";
  return null;
}

export function SetRow({ set }: { set: WorkoutSet }) {
  const entries = [...set.entries].sort((a, b) => a.entryOrder - b.entryOrder);
  const isDropset = set.setType === "dropset";
  const isWarmup = set.isWarmup;
  const rpe = Math.max(...entries.map((e) => e.rpe ?? 0), 0) || null;

  const className = ["set-row", isWarmup ? "set-warmup" : "", isDropset ? "set-dropset" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <li className={className}>
      <span className="set-number">{isWarmup ? "Calentamiento" : `Serie ${set.setNumber}`}</span>

      {isDropset ? (
        <span className="set-tramos">
          {entries.map((entry, index) => (
            <span key={entry.id} className="set-tramo">
              {index > 0 && <span className="set-tramo-arrow">→</span>}
              {fmtEntry(entry)} × {fmtWeight(entry.weight, entry.weightUnit)}
              {sideLabel(entry.side) && (
                <span className="set-side">({sideLabel(entry.side)})</span>
              )}
            </span>
          ))}
        </span>
      ) : (
        <span className="set-detail">
          {entries.map((entry) => (
            <span key={entry.id}>
              {fmtEntry(entry)} × {fmtWeight(entry.weight, entry.weightUnit)}
              {sideLabel(entry.side) && (
                <span className="set-side"> · {sideLabel(entry.side)}</span>
              )}
            </span>
          ))}
          {rpe != null && <span className="set-rpe">RPE {rpe}</span>}
        </span>
      )}

      {!isWarmup && set.setType !== "normal" && (
        <span className="set-type">{translateSetType(set.setType)}</span>
      )}
      {!isWarmup && set.volumeKg > 0 && (
        <span className="set-volume">{Math.round(set.volumeKg)} kg</span>
      )}
    </li>
  );
}
