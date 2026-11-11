"use client";

import { useRef, useState } from "react";

import { translateSetType } from "@/lib/labels";
import { canComplete, effectiveValues } from "@/lib/workout/ops";
import type { WorkoutExercise, WorkoutSet } from "@/lib/workout/types";

const TYPE_BADGE: Record<WorkoutSet["type"], string> = {
  normal: "",
  calentamiento: "C",
  dropset: "D",
  al_fallo: "F",
};

type Props = {
  ex: WorkoutExercise;
  index: number;
  onPatch: (patch: Partial<Pick<WorkoutSet, "weight" | "reps" | "rpe">>) => void;
  onCycleType: () => void;
  onToggleDone: () => void;
  onDelete: () => void;
};

function formatPrevious(prev: WorkoutExercise["previous"][number] | undefined): string {
  if (!prev || (prev.weightKg == null && prev.reps == null)) return "—";
  return `${prev.weightKg ?? "–"}×${prev.reps ?? "–"}`;
}

export function WorkoutSetRow({
  ex,
  index,
  onPatch,
  onCycleType,
  onToggleDone,
  onDelete,
}: Props) {
  const set = ex.sets[index];
  const prev = ex.previous[index];
  const eff = effectiveValues(ex, index);
  const repsRef = useRef<HTMLInputElement | null>(null);
  const [revealed, setRevealed] = useState(false);
  const touch = useRef<{ x: number; y: number } | null>(null);

  const workingNumber =
    ex.sets.slice(0, index + 1).filter((s) => s.type !== "calentamiento").length;
  const badge = TYPE_BADGE[set.type] || String(workingNumber);

  function handleDone() {
    if (!set.done && !canComplete(ex, index)) {
      repsRef.current?.focus();
      return;
    }
    onToggleDone();
  }

  return (
    <div className={`wk-row-wrap${revealed ? " revealed" : ""}`}>
      <div
        className={`wk-row${set.done ? " done" : ""}`}
        onTouchStart={(e) => {
          touch.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }}
        onTouchEnd={(e) => {
          const start = touch.current;
          touch.current = null;
          if (!start) return;
          const dx = e.changedTouches[0].clientX - start.x;
          const dy = e.changedTouches[0].clientY - start.y;
          if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.5) return;
          setRevealed(dx < 0);
        }}
      >
        <button
          type="button"
          className={`wk-type t-${set.type}`}
          onClick={onCycleType}
          aria-label={`Serie ${index + 1}, tipo ${translateSetType(set.type)}. Tocar para cambiar`}
          title={translateSetType(set.type)}
        >
          {badge}
        </button>
        <span className="wk-prev">{formatPrevious(prev)}</span>
        <input
          className="wk-input"
          inputMode="decimal"
          placeholder={eff.weight || "kg"}
          value={set.weight}
          aria-label="Peso en kg"
          onChange={(e) => onPatch({ weight: e.target.value })}
          onFocus={(e) => e.target.select()}
        />
        <input
          ref={repsRef}
          className="wk-input"
          inputMode="numeric"
          placeholder={eff.reps || "reps"}
          value={set.reps}
          aria-label="Repeticiones"
          onChange={(e) => onPatch({ reps: e.target.value })}
          onFocus={(e) => e.target.select()}
        />
        <input
          className="wk-input wk-rpe"
          inputMode="numeric"
          placeholder="RPE"
          value={set.rpe}
          aria-label="RPE (opcional)"
          onChange={(e) => onPatch({ rpe: e.target.value.replace(/\D/g, "").slice(0, 2) })}
          onFocus={(e) => e.target.select()}
        />
        <button
          type="button"
          className={`wk-check${set.done ? " on" : ""}`}
          aria-pressed={set.done}
          aria-label={set.done ? "Desmarcar serie" : "Marcar serie hecha"}
          onClick={handleDone}
        >
          ✓
        </button>
        <button
          type="button"
          className="wk-del-inline"
          aria-label="Eliminar serie"
          onClick={onDelete}
        >
          ×
        </button>
      </div>
      <button
        type="button"
        className="wk-del-swipe"
        tabIndex={revealed ? 0 : -1}
        onClick={onDelete}
      >
        Eliminar
      </button>
    </div>
  );
}
