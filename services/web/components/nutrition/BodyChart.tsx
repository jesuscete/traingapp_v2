"use client";

import { g1, shortDate } from "@/lib/nutrition";
import type { WeightPoint } from "@/lib/types";

const W = 340;
const H = 170;
const PAD = { l: 34, r: 44, t: 12, b: 26 };
const DAY_MS = 86_400_000;

type Line = { key: "weight" | "fat" | "muscle"; label: string; axis: "kg" | "pct"; pick: (p: WeightPoint) => number | null | undefined };

const LINES: Line[] = [
  { key: "weight", label: "Peso", axis: "kg", pick: (p) => p.weightKg },
  { key: "fat", label: "% graso", axis: "pct", pick: (p) => p.bodyFatPct },
  { key: "muscle", label: "% músculo", axis: "pct", pick: (p) => p.musclePct },
];

function range(values: number[], minSpan: number): [number, number] {
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (hi - lo < minSpan) {
    const mid = (hi + lo) / 2;
    lo = mid - minSpan / 2;
    hi = mid + minSpan / 2;
  }
  const pad = (hi - lo) * 0.08;
  return [lo - pad, hi + pad];
}

const t = (iso: string) => new Date(`${iso}T00:00:00Z`).getTime() / DAY_MS;

/** Peso (eje izq., kg) y % graso / % músculo (eje dcho., %) en una sola gráfica. */
export function BodyChart({ points }: { points: WeightPoint[] }) {
  const x0 = t(points[0].measuredOn);
  const x1 = Math.max(x0 + 1, t(points[points.length - 1].measuredOn));
  const pw = W - PAD.l - PAD.r;
  const ph = H - PAD.t - PAD.b;
  const x = (iso: string) => PAD.l + ((t(iso) - x0) / (x1 - x0)) * pw;

  // Cada serie con su propia escala: lo que importa es la tendencia de cada una
  // (un 18 % graso y un 41 % de músculo en el mismo eje saldrían planos).
  const drawn = LINES.map((line) => {
    const pts = points
      .map((p) => ({ iso: p.measuredOn, v: line.pick(p) }))
      .filter((p): p is { iso: string; v: number } => p.v != null);
    const [lo, hi] = pts.length ? range(pts.map((p) => p.v), line.axis === "kg" ? 2 : 1.5) : [0, 1];
    const y = (v: number) => PAD.t + ((hi - v) / (hi - lo)) * ph;
    return { line, pts, y };
  }).filter(({ line, pts }) => pts.length >= (line.axis === "kg" ? 1 : 2));
  const [kgLo, kgHi] = range(points.map((p) => p.weightKg), 2);
  const grid = [0, 0.5, 1].map((f) => PAD.t + f * ph);
  const kgAt = (gy: number) => kgHi - ((gy - PAD.t) / ph) * (kgHi - kgLo);

  return (
    <figure className="bc">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Evolución de peso y composición corporal">
        {grid.map((gy) => (
          <g key={gy}>
            <line x1={PAD.l} x2={W - PAD.r} y1={gy} y2={gy} className="lc-grid" />
            <text x={PAD.l - 4} y={gy + 3} textAnchor="end" className="lc-tick">
              {g1(kgAt(gy))}
            </text>
          </g>
        ))}
        {drawn.map(({ line, pts, y }) => (
          <g key={line.key} className={`bc-${line.key}`}>
            <path
              d={pts.map((p, i) => `${i ? "L" : "M"}${x(p.iso).toFixed(1)},${y(p.v).toFixed(1)}`).join(" ")}
              fill="none"
              className="bc-line"
            />
            {pts.map((p, i) => (
              <circle
                key={p.iso}
                cx={x(p.iso)}
                cy={y(p.v)}
                r={i === pts.length - 1 ? 3.5 : 2.2}
                className="bc-dot"
              />
            ))}
            {line.axis === "pct" && (
              <text x={W - PAD.r + 6} y={y(pts[pts.length - 1].v) + 3} className="lc-tick bc-end">
                {g1(pts[pts.length - 1].v)}%
              </text>
            )}
          </g>
        ))}
        <text x={PAD.l} y={H - 4} className="lc-tick">
          {shortDate(points[0].measuredOn)}
        </text>
        <text x={W - PAD.r} y={H - 4} textAnchor="end" className="lc-tick">
          {shortDate(points[points.length - 1].measuredOn)}
        </text>
      </svg>
      <figcaption className="bc-legend">
        {drawn.map(({ line }) => (
          <span key={line.key} className={`bc-${line.key}`}>
            <i /> {line.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
