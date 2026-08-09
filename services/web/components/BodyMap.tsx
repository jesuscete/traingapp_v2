import { translateMuscleGroup } from "@/lib/labels";
import type { MuscleImpact } from "@/lib/types";

const BASE_RGB = [42, 46, 56];
const HOT_RGB = [255, 77, 77];

function fillFor(activation: number | undefined): string {
  if (activation === undefined) return `rgb(${BASE_RGB.join(", ")})`;
  const t = Math.max(0, Math.min(1, activation));
  const r = Math.round(BASE_RGB[0] + (HOT_RGB[0] - BASE_RGB[0]) * t);
  const g = Math.round(BASE_RGB[1] + (HOT_RGB[1] - BASE_RGB[1]) * t);
  const b = Math.round(BASE_RGB[2] + (HOT_RGB[2] - BASE_RGB[2]) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

type Rect = { id: string; x: number; y: number; w: number; h: number };

const FRONT: Rect[] = [
  { id: "neck", x: 91, y: 40, w: 18, h: 18 },
  { id: "shoulders", x: 30, y: 58, w: 30, h: 40 },
  { id: "shoulders", x: 140, y: 58, w: 30, h: 40 },
  { id: "chest", x: 40, y: 102, w: 30, h: 48 },
  { id: "chest", x: 130, y: 102, w: 30, h: 48 },
  { id: "core", x: 74, y: 150, w: 52, h: 72 },
  { id: "biceps", x: 22, y: 152, w: 24, h: 48 },
  { id: "biceps", x: 154, y: 152, w: 24, h: 48 },
  { id: "forearms", x: 18, y: 204, w: 20, h: 64 },
  { id: "forearms", x: 162, y: 204, w: 20, h: 64 },
  { id: "quadriceps", x: 58, y: 246, w: 36, h: 86 },
  { id: "quadriceps", x: 106, y: 246, w: 36, h: 86 },
  { id: "calves", x: 60, y: 346, w: 30, h: 58 },
  { id: "calves", x: 110, y: 346, w: 30, h: 58 },
];

const BACK: Rect[] = [
  { id: "back", x: 60, y: 50, w: 80, h: 122 },
  { id: "triceps", x: 22, y: 152, w: 24, h: 48 },
  { id: "triceps", x: 154, y: 152, w: 24, h: 48 },
  { id: "glutes", x: 60, y: 178, w: 36, h: 42 },
  { id: "glutes", x: 104, y: 178, w: 36, h: 42 },
  { id: "hamstrings", x: 58, y: 226, w: 36, h: 82 },
  { id: "hamstrings", x: 106, y: 226, w: 36, h: 82 },
  { id: "calves", x: 60, y: 330, w: 30, h: 58 },
  { id: "calves", x: 110, y: 330, w: 30, h: 58 },
];

const HEAD = { cx: 100, cy: 18, rx: 20, ry: 22 };

function Silhouette({ regions, impacts }: { regions: Rect[]; impacts: Map<string, number> }) {
  return (
    <svg viewBox="0 0 200 420" className="bodymap-svg" role="img" aria-label="Heatmap muscular">
      <ellipse cx={HEAD.cx} cy={HEAD.cy} rx={HEAD.rx} ry={HEAD.ry} fill={BASE_RGB.join(", ")} />
      {regions.map((region, index) => {
        const activation = impacts.get(region.id);
        return (
          <rect
            key={`${region.id}-${index}`}
            x={region.x}
            y={region.y}
            width={region.w}
            height={region.h}
            rx="7"
            fill={fillFor(activation)}
          >
            <title>
              {translateMuscleGroup(region.id)}
              {activation !== undefined ? ` · ${Math.round(activation * 100)}%` : " · sin datos"}
            </title>
          </rect>
        );
      })}
    </svg>
  );
}

export function BodyMap({ impacts }: { impacts: MuscleImpact[] }) {
  const byGroup = new Map(impacts.map((item) => [item.muscleGroup, item.activation]));

  return (
    <div className="bodymap">
      <div className="bodymap-figure">
        <Silhouette regions={FRONT} impacts={byGroup} />
        <p className="muted">Frente</p>
      </div>
      <div className="bodymap-figure">
        <Silhouette regions={BACK} impacts={byGroup} />
        <p className="muted">Espalda</p>
      </div>
      <div className="bodymap-legend">
        {impacts.map((item) => (
          <span key={item.muscleGroup} className="chip">
            {translateMuscleGroup(item.muscleGroup)} · {Math.round(item.activation * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}
