import type { Session } from "@/lib/types";

export function ProgressPlaceholder({ session }: { session: Session }) {
  return (
    <section className="block">
      <h2>Cómo vas avanzando</h2>
      <div className="progress-placeholder">
        <p>
          Según el tipo de entreno ({session.discipline}) y la intensidad registrada,
          aquí se mostrará tu progresión en esta disciplina.
        </p>
        <p className="muted">Esta sección está pendiente de desarrollar.</p>
      </div>
    </section>
  );
}
