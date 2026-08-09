export type BreakdownRow = { label: string; value: string };

export function DisciplineBreakdown({
  title,
  subtitle,
  rows,
  empty,
}: {
  title: string;
  subtitle?: string;
  rows: BreakdownRow[];
  empty: string;
}) {
  return (
    <section className="block">
      <h2>{title}</h2>
      {subtitle && <p className="muted">{subtitle}</p>}
      {rows.length === 0 ? (
        <p className="muted">{empty}</p>
      ) : (
        <ul className="breakdown-list">
          {rows.map((row) => (
            <li key={row.label} className="breakdown-row">
              <span className="breakdown-label">{row.label}</span>
              <span className="breakdown-value">{row.value}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
