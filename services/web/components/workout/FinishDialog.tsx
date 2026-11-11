"use client";

type Props = {
  setsDone: number;
  setsPending: number;
  exercisesDiscarded: number;
  busy: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
  onDiscard: () => void;
};

export function FinishDialog({
  setsDone,
  setsPending,
  exercisesDiscarded,
  busy,
  error,
  onConfirm,
  onCancel,
  onDiscard,
}: Props) {
  const empty = setsDone === 0;
  return (
    <div className="sheet-backdrop center" role="presentation" onClick={busy ? undefined : onCancel}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Terminar entreno"
        onClick={(e) => e.stopPropagation()}
      >
        <h3>{empty ? "Nada que guardar" : "¿Terminar el entreno?"}</h3>
        {empty ? (
          <p className="muted">No has marcado ninguna serie como hecha.</p>
        ) : (
          <p className="muted">
            Se guardarán {setsDone} serie{setsDone === 1 ? "" : "s"} hecha
            {setsDone === 1 ? "" : "s"}.
          </p>
        )}
        {setsPending > 0 && !empty && (
          <p className="wk-warn">
            {setsPending} serie{setsPending === 1 ? "" : "s"} sin marcar no se guardará
            {setsPending === 1 ? "" : "n"}
            {exercisesDiscarded > 0
              ? `; ${exercisesDiscarded} ejercicio${exercisesDiscarded === 1 ? "" : "s"} sin series hechas se descartará${exercisesDiscarded === 1 ? "" : "n"}`
              : ""}
            .
          </p>
        )}
        {error && <p className="error">{error}</p>}
        <div className="dialog-actions">
          {!empty && (
            <button type="button" className="wk-primary" disabled={busy} onClick={onConfirm}>
              {busy ? "Guardando…" : "Guardar entreno"}
            </button>
          )}
          <button type="button" className="secondary" disabled={busy} onClick={onCancel}>
            Seguir entrenando
          </button>
          <button type="button" className="wk-danger" disabled={busy} onClick={onDiscard}>
            Descartar entreno
          </button>
        </div>
      </div>
    </div>
  );
}
