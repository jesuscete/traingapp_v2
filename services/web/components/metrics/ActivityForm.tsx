"use client";

import { useState } from "react";

import { MetricsEditor } from "@/components/metrics/MetricsEditor";
import {
  emptyMetricsForm,
  formToMetrics,
  metricsKindFor,
  totalCombatMinutes,
  type MetricsForm,
  type MetricsResult,
} from "@/lib/metrics";

export type ActivityValues = {
  performedAt: string; // formato datetime-local
  durationMinutes: string;
  intensity: number | null;
  note: string;
  metricsForm: MetricsForm;
};

export type ActivitySubmit = {
  performedAtIso: string;
  durationMinutes: number | null;
  intensity: number | null;
  note: string;
  metrics: MetricsResult["metrics"];
};

type Props = {
  discipline: string;
  /** Sin editor de métricas (sesiones de gimnasio). */
  headerOnly?: boolean;
  initial: ActivityValues;
  submitLabel: string;
  busy: boolean;
  error: string | null;
  onSubmit: (data: ActivitySubmit) => void;
  onCancel?: () => void;
};

export function toLocalInput(iso: string | Date): string {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function ActivityForm({
  discipline,
  headerOnly = false,
  initial,
  submitLabel,
  busy,
  error,
  onSubmit,
  onCancel,
}: Props) {
  const [values, setValues] = useState<ActivityValues>(initial);
  const [localError, setLocalError] = useState<string | null>(null);
  const kind = metricsKindFor(discipline);
  const [prevKind, setPrevKind] = useState(kind);
  if (prevKind !== kind) {
    setPrevKind(kind);
    setValues((prev) => ({ ...prev, metricsForm: emptyMetricsForm() }));
  }
  const patch = (changes: Partial<ActivityValues>) =>
    setValues((prev) => ({ ...prev, ...changes }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setLocalError(null);

    const date = new Date(values.performedAt);
    if (!values.performedAt || Number.isNaN(date.getTime())) {
      setLocalError("Indica una fecha y hora válidas.");
      return;
    }
    let duration: number | null = null;
    if (values.durationMinutes.trim()) {
      const n = Number(values.durationMinutes.replace(",", "."));
      if (!Number.isFinite(n) || n <= 0 || n > 1440) {
        setLocalError("La duración debe estar entre 1 y 1440 minutos.");
        return;
      }
      duration = Math.round(n);
    }

    let metrics: MetricsResult["metrics"] = null;
    if (!headerOnly) {
      const result = formToMetrics(kind, values.metricsForm);
      if (result.error) {
        setLocalError(result.error);
        return;
      }
      metrics = result.metrics;
    }

    const hasCombatTime =
      !headerOnly && kind === "combat" && totalCombatMinutes(values.metricsForm.blocks) > 0;
    if (duration == null && !hasCombatTime) {
      setLocalError("Indica la duración en minutos.");
      return;
    }

    onSubmit({
      performedAtIso: date.toISOString(),
      durationMinutes: duration,
      intensity: values.intensity,
      note: values.note.trim(),
      metrics,
    });
  }

  const shownError = localError ?? error;

  return (
    <form className="m3-form" onSubmit={submit}>
      <section className="block m3-block">
        <h2>General</h2>
        <label className="m3-field">
          <span>Fecha y hora</span>
          <input
            type="datetime-local"
            value={values.performedAt}
            onChange={(e) => patch({ performedAt: e.target.value })}
            required
          />
        </label>
        <label className="m3-field">
          <span>
            Duración (min)
            {kind === "combat" && !headerOnly ? " · opcional, se calcula de los bloques" : ""}
          </span>
          <input
            type="number"
            inputMode="numeric"
            min={1}
            max={1440}
            value={values.durationMinutes}
            onChange={(e) => patch({ durationMinutes: e.target.value })}
          />
        </label>
        <div className="m3-field">
          <span>Intensidad (RPE 1-10)</span>
          <div className="m3-rpe" role="group" aria-label="RPE">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <button
                key={n}
                type="button"
                className={values.intensity === n ? "on" : ""}
                aria-pressed={values.intensity === n}
                onClick={() => patch({ intensity: values.intensity === n ? null : n })}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <label className="m3-field">
          <span>Nota</span>
          <textarea
            rows={2}
            value={values.note}
            onChange={(e) => patch({ note: e.target.value })}
          />
        </label>
      </section>

      {!headerOnly && (
        <MetricsEditor
          kind={kind}
          discipline={discipline}
          value={values.metricsForm}
          onChange={(metricsForm) => patch({ metricsForm })}
          durationMinutes={values.durationMinutes}
        />
      )}

      {shownError && <p className="error">{shownError}</p>}

      <div className="m3-submit">
        {onCancel && (
          <button type="button" className="secondary" onClick={onCancel} disabled={busy}>
            Cancelar
          </button>
        )}
        <button type="submit" disabled={busy}>
          {busy ? "Guardando..." : submitLabel}
        </button>
      </div>
    </form>
  );
}
