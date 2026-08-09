type CaloriesInfo = {
  calories?: number | null;
  estimatedKcal?: number | null;
};

export function CaloriesCard({ session }: { session: CaloriesInfo }) {
  const registered = session.calories ?? null;
  const estimated = session.estimatedKcal ?? null;
  if (registered == null && estimated == null) return null;

  const value: number = registered ?? estimated ?? 0;
  const label =
    registered != null
      ? "Calorías registradas"
      : "Calorías estimadas (MET, valor aproximado)";

  return (
    <section className="block">
      <h2>Calorías quemadas</h2>
      <div className="stats">
        <div className="stat-card">
          <span className="stat-label">{label}</span>
          <span className="stat-value">{Math.round(value)} kcal</span>
        </div>
      </div>
    </section>
  );
}
