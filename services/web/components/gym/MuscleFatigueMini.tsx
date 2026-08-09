import { translateMuscleGroup } from "@/lib/labels";
import type { MuscleImpact } from "@/lib/types";

export function MuscleFatigueMini({ impacts }: { impacts: MuscleImpact[] }) {
  if (impacts.length === 0) return null;

  const sum = impacts.reduce((total, item) => total + item.activation, 0) || 1;

  return (
    <div className="muscle-mini">
      <div
        className="muscle-mini-bar"
        role="img"
        aria-label="Distribución de fatiga por grupo muscular"
      >
        {impacts.map((item) => (
          <span
            key={item.muscleGroup}
            className="muscle-mini-seg"
            style={{
              width: `${(item.activation / sum) * 100}%`,
              opacity: 0.35 + 0.65 * item.activation,
            }}
          >
            <title>{translateMuscleGroup(item.muscleGroup)}</title>
          </span>
        ))}
      </div>
      <ul className="muscle-mini-list">
        {impacts.map((item) => (
          <li key={item.muscleGroup}>
            <span className="muscle-mini-name">{translateMuscleGroup(item.muscleGroup)}</span>
            <span className="muscle-mini-track">
              <span
                className="muscle-mini-fill"
                style={{ width: `${Math.round(item.activation * 100)}%` }}
              />
            </span>
            <span className="muscle-mini-pct">{Math.round(item.activation * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
