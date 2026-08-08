type RadarPoint = { label: string; value: number };

function point(cx: number, cy: number, radius: number, angle: number): string {
  const x = cx + radius * Math.cos(angle);
  const y = cy + radius * Math.sin(angle);
  return `${x.toFixed(1)},${y.toFixed(1)}`;
}

export function RadarChart({
  data,
  size = 280,
  showLabels = false,
}: {
  data: RadarPoint[];
  size?: number;
  showLabels?: boolean;
}) {
  if (data.length === 0) return null;

  const cx = size / 2;
  const cy = size / 2;
  const radius = (size / 2) * 0.72;
  const slice = (Math.PI * 2) / data.length;
  const offset = -Math.PI / 2;

  const points = (scale: number) =>
    data
      .map((item, i) => point(cx, cy, radius * scale, offset + i * slice))
      .join(" ");

  const dataPoints = data
    .map((item, i) =>
      point(cx, cy, radius * Math.max(0.02, Math.min(1, item.value)), offset + i * slice),
    )
    .join(" ");

  const labelRadius = radius + (size * 0.09);

  return (
    <svg className="radar" width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {[0.25, 0.5, 0.75, 1].map((ring) => (
        <polygon
          key={ring}
          points={points(ring)}
          className="radar-ring"
          fill="none"
        />
      ))}
      {data.map((_, i) => {
        const [x, y] = point(cx, cy, radius, offset + i * slice).split(",");
        return (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={x}
            y2={y}
            className="radar-axis"
          />
        );
      })}
      <polygon points={dataPoints} className="radar-fill" />
      {data.map((item, i) => {
        const [x, y] = point(
          cx,
          cy,
          radius * Math.max(0.02, Math.min(1, item.value)),
          offset + i * slice,
        ).split(",");
        return <circle key={i} cx={x} cy={y} r={3.5} className="radar-dot" />;
      })}
      {showLabels &&
        data.map((item, i) => {
          const angle = offset + i * slice;
          const lx = cx + labelRadius * Math.cos(angle);
          const ly = cy + labelRadius * Math.sin(angle);
          return (
            <text
              key={item.label}
              x={lx}
              y={ly}
              textAnchor={Math.abs(Math.cos(angle)) < 0.3 ? "middle" : Math.cos(angle) > 0 ? "start" : "end"}
              dominantBaseline="middle"
              className="radar-label"
            >
              {item.label}
            </text>
          );
        })}
    </svg>
  );
}
