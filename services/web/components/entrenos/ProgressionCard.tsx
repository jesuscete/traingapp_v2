import { translateDiscipline } from "@/lib/labels";
import type { DisciplineDelta } from "@/lib/types";

export function ProgressionCard({ deltas }: { deltas: DisciplineDelta[] }) {
  if (deltas.length === 0) return null;

  return (
    <section className="block">
      <h2>Progresión vs. periodo anterior</h2>
      <ul className="breakdown-list">
        {deltas.map((delta) => {
          const tone =
            delta.deltaPct == null || delta.deltaPct === 0
              ? "delta-flat"
              : delta.deltaPct > 0
                ? "delta-up"
                : "delta-down";
          const text =
            delta.deltaPct == null
              ? "nuevo"
              : delta.deltaPct === 0
                ? "sin cambios"
                : delta.deltaPct > 0
                  ? `+${delta.deltaPct}%`
                  : `${delta.deltaPct}%`;
          return (
            <li key={delta.discipline} className="breakdown-row">
              <span className="breakdown-label">
                {translateDiscipline(delta.discipline)}
              </span>
              <span className={`breakdown-value ${tone}`}>
                {delta.sessions} sesiones · {text}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
