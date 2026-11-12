export type ChartBand = { from: number; to: number; color: string };

export type ChartPoint = { x: number; y: number | null };

/** Reduce a ~maxPoints promediando por cubetas (los nulos se ignoran). */
export function downsample(points: ChartPoint[], maxPoints = 240): ChartPoint[] {
  if (points.length <= maxPoints) return points;
  const size = Math.ceil(points.length / maxPoints);
  const out: ChartPoint[] = [];
  for (let i = 0; i < points.length; i += size) {
    const chunk = points.slice(i, i + size);
    const values = chunk.filter((p): p is { x: number; y: number } => p.y != null);
    out.push({
      x: chunk[Math.floor(chunk.length / 2)].x,
      y: values.length ? values.reduce((a, p) => a + p.y, 0) / values.length : null,
    });
  }
  return out;
}

export function formatClock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
    : `${m}:${String(sec).padStart(2, "0")}`;
}

type Props = {
  points: ChartPoint[];
  color: string;
  /** Eje Y: valor -> etiqueta. */
  formatY: (value: number) => string;
  /** Rango Y manual; si no, se calcula de los datos. */
  min?: number;
  max?: number;
  /** Mayor valor abajo (ritmo: menos s/km = más rápido = arriba). */
  invert?: boolean;
  bands?: ChartBand[];
  fill?: boolean;
  label: string;
};

const WIDTH = 560;
const HEIGHT = 180;
const PAD_L = 44;
const PAD_R = 8;
const PAD_T = 10;
const PAD_B = 22;

export function ActivityChart({
  points,
  color,
  formatY,
  min,
  max,
  invert = false,
  bands = [],
  fill = false,
  label,
}: Props) {
  const data = downsample(points);
  const ys = data.filter((p) => p.y != null).map((p) => p.y as number);
  if (data.length < 2 || ys.length < 2) return null;

  let lo = min ?? Math.min(...ys);
  let hi = max ?? Math.max(...ys);
  if (hi - lo < 1e-6) {
    lo -= 1;
    hi += 1;
  }
  const x0 = data[0].x;
  const x1 = data[data.length - 1].x;
  const spanX = x1 - x0 || 1;
  const plotW = WIDTH - PAD_L - PAD_R;
  const plotH = HEIGHT - PAD_T - PAD_B;

  const getX = (x: number) => PAD_L + ((x - x0) / spanX) * plotW;
  const frac = (v: number) => (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo);
  const getY = (v: number) => PAD_T + (invert ? frac(v) : 1 - frac(v)) * plotH;

  let d = "";
  let pen = false;
  let first: ChartPoint | null = null;
  let last: ChartPoint | null = null;
  for (const p of data) {
    if (p.y == null) {
      pen = false;
      continue;
    }
    d += `${pen ? "L" : "M"}${getX(p.x).toFixed(1)},${getY(p.y).toFixed(1)} `;
    pen = true;
    first = first ?? p;
    last = p;
  }

  const yTicks = Array.from({ length: 5 }, (_, i) => lo + ((hi - lo) / 4) * i);
  const xTicks = Array.from({ length: 5 }, (_, i) => x0 + (spanX / 4) * i);
  const baseY = PAD_T + plotH;

  return (
    <svg
      className="act-chart line-chart"
      width="100%"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={label}
    >
      {bands.map((b, i) => {
        const yA = getY(Math.max(lo, Math.min(hi, b.from)));
        const yB = getY(Math.max(lo, Math.min(hi, b.to)));
        if (b.to <= lo || b.from >= hi) return null;
        return (
          <rect
            key={i}
            x={PAD_L}
            width={plotW}
            y={Math.min(yA, yB)}
            height={Math.abs(yA - yB)}
            fill={b.color}
            opacity={0.18}
          />
        );
      })}
      {yTicks.map((v) => (
        <g key={v}>
          <line x1={PAD_L} x2={WIDTH - PAD_R} y1={getY(v)} y2={getY(v)} className="lc-grid" />
          <text x={PAD_L - 6} y={getY(v) + 3} textAnchor="end" className="lc-tick">
            {formatY(v)}
          </text>
        </g>
      ))}
      {xTicks.map((x) => (
        <text key={x} x={getX(x)} y={HEIGHT - 6} textAnchor="middle" className="lc-tick">
          {formatClock(x)}
        </text>
      ))}
      {fill && first && last && (
        <path
          d={`${d}L${getX(last.x).toFixed(1)},${baseY} L${getX(first.x).toFixed(1)},${baseY} Z`}
          fill={color}
          opacity={0.25}
          stroke="none"
        />
      )}
      <path d={d.trim()} className="lc-line" style={{ stroke: color }} fill="none" />
    </svg>
  );
}
