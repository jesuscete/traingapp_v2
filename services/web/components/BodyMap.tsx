import { translateMuscleGroup } from "@/lib/labels";

export type BodyMapPoint = { muscleGroup: string; value: number };

const BASE_RGB = [42, 46, 56];
const HOT_RGB = [255, 77, 77];

function fillFor(value: number | undefined): string {
  if (value === undefined) return `rgb(${BASE_RGB.join(", ")})`;
  const t = Math.max(0, Math.min(1, value));
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

function Silhouette({ regions, values }: { regions: Rect[]; values: Map<string, number> }) {
  return (
    <svg viewBox="0 0 200 420" className="bodymap-svg" role="img" aria-label="Heatmap muscular">
      <ellipse cx={HEAD.cx} cy={HEAD.cy} rx={HEAD.rx} ry={HEAD.ry} fill={BASE_RGB.join(", ")} />
      {regions.map((region, index) => {
        const value = values.get(region.id);
        return (
          <rect
            key={`${region.id}-${index}`}
            x={region.x}
            y={region.y}
            width={region.w}
            height={region.h}
            rx="7"
            fill={fillFor(value)}
          >
            <title>
              {translateMuscleGroup(region.id)}
              {value !== undefined ? ` · ${Math.round(value * 100)}%` : " · sin datos"}
            </title>
          </rect>
        );
      })}
    </svg>
  );
}

export function BodyMap({
  points,
  showLegend = true,
}: {
  points: BodyMapPoint[];
  showLegend?: boolean;
}) {
  const byGroup = new Map(points.map((item) => [item.muscleGroup, item.value]));

  return (
    <div className="bodymap">
      <div className="bodymap-figure">
        <Silhouette regions={FRONT} values={byGroup} />
        <p className="muted">Frente</p>
      </div>
      <div className="bodymap-figure">
        <Silhouette regions={BACK} values={byGroup} />
        <p className="muted">Espalda</p>
      </div>
      {showLegend && (
        <div className="bodymap-legend">
          {points.map((item) => (
            <span key={item.muscleGroup} className="chip">
              {translateMuscleGroup(item.muscleGroup)} · {Math.round(item.value * 100)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
