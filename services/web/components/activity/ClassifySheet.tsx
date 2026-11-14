"use client";

import { Sparkles } from "lucide-react";
import { useState } from "react";

import { DisciplineIcon } from "@/components/icons";
import { Sheet } from "@/components/nutrition/Sheet";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { DISCIPLINE_LABELS, translateDiscipline } from "@/lib/labels";
import { dayLabel, kcal, toISODate } from "@/lib/nutrition";
import type { ClassifyPreview, PendingWatch } from "@/lib/types";

/** Lo más habitual con el reloj en modo «Cardio»; el resto va en «Otra». */
const QUICK = ["hyrox", "crossfit", "boxing", "football", "gym", "martial_arts", "running", "cycling"];
const WATCH_MODE: Record<string, string> = {
  cardio_training: "Cardio",
  hiit: "HIIT",
  training: "Entreno",
  generic: "Genérico",
  fitness_equipment: "Máquinas",
};

function watchMode(item: PendingWatch): string {
  return WATCH_MODE[item.subSport ?? ""] ?? WATCH_MODE[item.sport ?? ""] ?? "Actividad";
}

function when(iso: string): string {
  const d = new Date(iso);
  return `${dayLabel(toISODate(d))} · ${d.toLocaleTimeString("es-ES", { hour: "2-digit", minute: "2-digit" })}`;
}

function wodScheme(p: ClassifyPreview): string | null {
  return p.metrics?.kind === "wod" ? (p.metrics.scheme ?? (p.metrics.rounds ? `${p.metrics.rounds} rondas` : null)) : null;
}

/** Lo que la IA ha entendido: ejercicios sueltos o movimientos del WOD. */
function previewLines(p: ClassifyPreview): string[] {
  if (p.exercises.length > 0)
    return p.exercises.map((e) => `${e.name}${e.sets ? ` · ${e.sets}×${e.reps ?? "?"}` : e.reps ? ` · ${e.reps} reps` : ""}`);
  if (p.metrics?.kind === "wod")
    return (p.metrics.movements ?? []).map((m) => {
      const amount = m.distanceM ? `${m.distanceM} m` : m.reps ? `${m.reps}` : m.calories ? `${m.calories} cal` : "";
      return `${amount ? `${amount} ` : ""}${m.name}${m.weightKg ? ` (${m.weightKg} kg)` : ""}`;
    });
  return [];
}

type Props = {
  token: string;
  items: PendingWatch[];
  onClose: () => void;
  /** Se llama tras catalogar o descartar cada entreno. */
  onChanged: () => void;
};

export function ClassifySheet({ token, items, onClose, onChanged }: Props) {
  const [index, setIndex] = useState(0);
  const [discipline, setDiscipline] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<ClassifyPreview | null>(null);
  const [intensity, setIntensity] = useState<number | null>(null);
  const [busy, setBusy] = useState<"ai" | "save" | "skip" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmSkip, setConfirmSkip] = useState(false);

  const item = items[index];
  if (!item) return null;
  const others = Object.keys(DISCIPLINE_LABELS).filter((d) => !QUICK.includes(d) && d !== "other");

  function next() {
    onChanged();
    setDiscipline(null);
    setText("");
    setPreview(null);
    setIntensity(null);
    setError(null);
    setConfirmSkip(false);
    if (index + 1 < items.length) setIndex(index + 1);
    else onClose();
  }

  async function interpret() {
    setBusy("ai");
    setError(null);
    try {
      const result = await api.classifyPreview(token, text);
      setPreview(result);
      if (result.discipline && result.discipline !== "other") setDiscipline(result.discipline);
      if (result.intensity) setIntensity(result.intensity);
    } catch (err) {
      setError(err instanceof Error ? err.message : "La IA no ha podido interpretarlo");
    } finally {
      setBusy(null);
    }
  }

  async function save() {
    if (!discipline) return;
    setBusy("save");
    setError(null);
    try {
      const fromAi = preview !== null && preview.discipline === discipline;
      await api.classifySession(token, item.id, {
        discipline,
        note: text.trim() || undefined,
        intensity: intensity ?? undefined,
        exercises: preview && preview.exercises.length > 0 ? preview.exercises : undefined,
        metrics: fromAi ? preview.metrics : undefined,
      });
      next();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setBusy(null);
    }
  }

  async function skip() {
    setBusy("skip");
    setError(null);
    try {
      await api.skipClassification(token, item.id);
      next();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setBusy(null);
    }
  }

  const footer = confirmSkip ? (
    <div className="cw-confirm">
      <p>
        Sin catalogar, la fatiga y el análisis usarán una estimación genérica y serán <b>menos precisos</b>. No te
        volveremos a preguntar por este entreno.
      </p>
      <div className="cw-actions">
        <Button variant="secondary" onClick={() => setConfirmSkip(false)}>
          Volver
        </Button>
        <Button variant="danger" onClick={() => void skip()} disabled={busy !== null}>
          {busy === "skip" ? "Guardando…" : "No catalogar"}
        </Button>
      </div>
    </div>
  ) : (
    <div className="cw-actions">
      <Button variant="text" onClick={() => setConfirmSkip(true)} disabled={busy !== null}>
        No catalogar
      </Button>
      <Button onClick={() => void save()} disabled={!discipline || busy !== null}>
        {busy === "save" ? "Guardando…" : discipline ? `Guardar como ${translateDiscipline(discipline)}` : "Elige la actividad"}
      </Button>
    </div>
  );

  return (
    <Sheet
      title={items.length > 1 ? `Entreno del reloj (${index + 1}/${items.length})` : "Entreno del reloj"}
      onClose={onClose}
      footer={footer}
    >
      <div className="cw">
        <div className="cw-head">
          <span className="cw-mode">Modo del reloj: {watchMode(item)}</span>
          <strong>{when(item.performedAt)}</strong>
          <div className="cw-stats">
            {item.durationMinutes != null && <span>{formatDuration(item.durationMinutes)}</span>}
            {item.avgHeartRate != null && (
              <span>
                FC {Math.round(item.avgHeartRate)}
                {item.maxHeartRate != null ? `/${Math.round(item.maxHeartRate)}` : ""} ppm
              </span>
            )}
            {item.estimatedKcal != null && <span>{kcal(item.estimatedKcal)} kcal</span>}
          </div>
        </div>

        <p className="cw-label">¿Qué actividad fue?</p>
        <div className="cw-chips">
          {QUICK.map((d) => (
            <button
              key={d}
              type="button"
              className={`cw-chip${discipline === d ? " on" : ""}`}
              onClick={() => setDiscipline(d)}
              aria-pressed={discipline === d}
            >
              <DisciplineIcon discipline={d} size={18} />
              {translateDiscipline(d)}
            </button>
          ))}
        </div>
        <select
          className="cw-select"
          value={discipline && !QUICK.includes(discipline) ? discipline : ""}
          onChange={(e) => setDiscipline(e.target.value || null)}
          aria-label="Otra actividad"
        >
          <option value="">Otra actividad…</option>
          {others.map((d) => (
            <option key={d} value={d}>
              {translateDiscipline(d)}
            </option>
          ))}
        </select>

        <p className="cw-label">
          Cuéntame qué hiciste <span className="muted">(opcional, afina la fatiga)</span>
        </p>
        <textarea
          className="cw-text"
          rows={3}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPreview(null);
          }}
          placeholder="Ej.: HYROX simulado, 4 rondas de 1 km corriendo + 20 wall balls + 15 burpees"
        />
        <Button variant="secondary" onClick={() => void interpret()} disabled={text.trim().length < 3 || busy !== null}>
          <Sparkles size={16} strokeWidth={1.75} aria-hidden="true" />
          {busy === "ai" ? "Interpretando…" : "Interpretar con IA"}
        </Button>
        {preview && (
          <div className="cw-preview">
            <p>
              <b>He entendido:</b> {preview.discipline ? translateDiscipline(preview.discipline) : "actividad sin identificar"}
              {wodScheme(preview) ? ` · ${wodScheme(preview)}` : ""}
            </p>
            {previewLines(preview).length > 0 && (
              <ul>
                {previewLines(preview).map((line, i) => (
                  <li key={`${line}-${i}`}>{line}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <p className="cw-label">
          Esfuerzo percibido <span className="muted">{intensity ? `${intensity}/10` : "(opcional)"}</span>
        </p>
        <div className="cw-rpe">
          {Array.from({ length: 10 }, (_, i) => i + 1).map((v) => (
            <button
              key={v}
              type="button"
              className={`cw-rpe-btn${intensity === v ? " on" : ""}`}
              onClick={() => setIntensity(intensity === v ? null : v)}
              aria-pressed={intensity === v}
            >
              {v}
            </button>
          ))}
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </Sheet>
  );
}
