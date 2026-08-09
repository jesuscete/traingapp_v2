export type LineSeries = {
  name: string;
  color: string;
  points: (number | null)[];
};

function path(
  points: (number | null)[],
  getX: (i: number) => number,
  getY: (v: number) => number,
): string {
  let d = "";
  let pen = false;
  points.forEach((value, i) => {
    if (value == null) {
      pen = false;
      return;
    }
    const cmd = pen ? "L" : "M";
    d += `${cmd}${getX(i).toFixed(1)},${getY(value).toFixed(1)} `;
    pen = true;
  });
  return d.trim();
}

export function LineChart({
  labels,
  series,
  width = 560,
  height = 200,
  min,
  max,
}: {
  labels: string[];
  series: LineSeries[];
  width?: number;
  height?: number;
  min?: number;
  max?: number;
}) {
  if (labels.length === 0) return null;

  const padX = 34;
  const padY = 16;
  const plotW = width - padX - 6;
  const plotH = height - padY - 22;

  const lo = min ?? 0;
  const hi = max ?? 100;
  const range = hi - lo || 1;

  const getX = (i: number) =>
    padX + (labels.length === 1 ? plotW / 2 : (i / (labels.length - 1)) * plotW);
  const getY = (v: number) =>
    padY + ((hi - Math.max(lo, Math.min(hi, v))) / range) * plotH;

  const ticks = 5;
  const gridLines = Array.from({ length: ticks + 1 }, (_, i) =>
    lo + (range / ticks) * i,
  );

  const labelStep = Math.max(1, Math.ceil(labels.length / 6));

  return (
    <svg
      className="line-chart"
      width="100%"
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
    >
      {gridLines.map((value) => {
        const y = getY(value);
        return (
          <g key={value}>
            <line x1={padX} x2={width - 6} y1={y} y2={y} className="lc-grid" />
            <text x={padX - 6} y={y + 3} textAnchor="end" className="lc-tick">
              {Math.round(value)}
            </text>
          </g>
        );
      })}
      {labels.map((label, i) =>
        i % labelStep === 0 ? (
          <text
            key={`${label}-${i}`}
            x={getX(i)}
            y={height - 6}
            textAnchor="middle"
            className="lc-tick"
          >
            {label}
          </text>
        ) : null,
      )}
      {series.map((s) => (
        <path
          key={s.name}
          d={path(s.points, getX, getY)}
          fill="none"
          className="lc-line"
          style={{ stroke: s.color }}
        />
      ))}
    </svg>
  );
}
