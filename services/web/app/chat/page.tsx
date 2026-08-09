"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BodyMap } from "@/components/BodyMap";
import { BottomNav } from "@/components/BottomNav";
import { ChatComposer } from "@/components/ChatComposer";
import { translateDiscipline } from "@/lib/labels";
import type {
  ExerciseDraft,
  Session,
  WorkoutDraft,
} from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

type Phase = "idle" | "live" | "review" | "done";

const CARDIO_DISCIPLINES = ["boxing", "running", "cycling", "swimming", "other"];
const DISTANCE_DISCIPLINES = ["running", "cycling", "swimming"];

const WORKOUT_TYPES: Record<string, string> = {
  recovery: "Recuperación",
  easy: "Fácil",
  tempo: "Tempo",
  interval: "Intervalos",
  fartlek: "Fartlek",
  long: "Largo",
};

const PLACEHOLDERS: Record<string, string> = {
  idle: 'Describe tu entreno o pregúntame (ej. "empecé entrenando pecho")',
  live: 'Anota la serie (ej. "press banca 5x5 80kg")',
};

function numberOrNull(value: string): number | null {
  const parsed = Number(value);
  return value === "" || Number.isNaN(parsed) ? null : parsed;
}

export default function Chat() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [text, setText] = useState("");
  const [entries, setEntries] = useState<string[]>([]);
  const [requestId, setRequestId] = useState<string | null>(null);
  const [draft, setDraft] = useState<WorkoutDraft | null>(null);
  const [edits, setEdits] = useState<ExerciseDraft[]>([]);
  const [rpe, setRpe] = useState(7);
  const [fatigue, setFatigue] = useState(5);
  const [durationMin, setDurationMin] = useState("");
  const [distanceKm, setDistanceKm] = useState("");
  const [workoutType, setWorkoutType] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
  }, [router]);

  function reset() {
    setPhase("idle");
    setText("");
    setEntries([]);
    setRequestId(null);
    setDraft(null);
    setEdits([]);
    setSession(null);
    setDurationMin("");
    setDistanceKm("");
    setWorkoutType("");
    setError(null);
  }

  function applyDraft(draftResponse: WorkoutDraft, nextRequestId: string | null) {
    setDraft(draftResponse);
    setEdits(draftResponse.exercises);
    setRequestId(nextRequestId);
    setRpe(draftResponse.suggestedRpe ?? 7);
    setDurationMin(
      draftResponse.durationMinutes != null ? String(draftResponse.durationMinutes) : "",
    );
    setDistanceKm("");
    setWorkoutType("");
  }

  async function send(value: string) {
    if (!token || !value.trim()) return;
    setBusy(true);
    setError(null);
    const raw = value.trim();
    setText("");
    try {
      const response = await api.sendDraft(token, raw);
      if (response.mode === "live") {
        if (response.entriesCount > 0) {
          setEntries((prev) => [...prev, raw]);
        }
        setPhase("live");
      } else if (response.mode === "confirm") {
        if (!response.draft) {
          setError("La IA no devolvió un borrador.");
          setPhase("idle");
          return;
        }
        applyDraft(response.draft, response.requestId ?? null);
        setPhase("review");
      } else {
        if (!response.draft) {
          setError("La IA no devolvió un borrador.");
          setPhase("idle");
          return;
        }
        applyDraft(response.draft, response.requestId ?? null);
        setPhase("review");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al procesar el mensaje");
    } finally {
      setBusy(false);
    }
  }

  function updateExercise(index: number, field: keyof ExerciseDraft, value: string) {
    setEdits((prev) =>
      prev.map((item, i) =>
        i === index
          ? { ...item, [field]: field === "name" ? value : numberOrNull(value) }
          : item,
      ),
    );
  }

  async function confirm() {
    if (!token || !requestId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.confirmDraft(token, {
        requestId,
        suggestedRpe: rpe,
        perceivedFatigue: fatigue,
        durationMinutes:
          durationMin !== "" ? (Number(durationMin) || null) : null,
        distanceMeters:
          distanceKm !== "" ? (Number(distanceKm) || 0) * 1000 : null,
        workoutType: workoutType !== "" ? workoutType : null,
        exercises: edits,
      });
      setSession(created);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al confirmar la sesión");
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!token || !requestId) return;
    setBusy(true);
    setError(null);
    try {
      await api.cancelDraft(token, requestId);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cancelar");
    } finally {
      setBusy(false);
    }
  }

  const entriesList = entries.length > 0 && (
    <ul className="chat-entries">
      {entries.map((entry, index) => (
        <li key={`${index}-${entry}`} className="chat-entry">
          {entry}
        </li>
      ))}
    </ul>
  );

  const isCardio =
    draft != null &&
    CARDIO_DISCIPLINES.includes(draft.discipline) &&
    edits.length === 0;

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>Asistente de entrenamiento</h2>
        <p className="subtitle">
          {phase === "live"
            ? "Anota tus series. Cuando termines, pulsa 'Terminar entreno'."
            : phase === "review"
              ? "Revisa y confirma el borrador de la IA."
              : "Registra tu entreno o pregúntame por tu rutina y progreso."}
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {phase === "idle" && (
        <form
          className="block"
          onSubmit={(event) => {
            event.preventDefault();
            send(text);
          }}
        >
          <ChatComposer
            placeholder={PLACEHOLDERS.idle}
            value={text}
            onChange={setText}
            onSubmit={() => send(text)}
            disabled={busy}
            hint="Enter para enviar · puedo registrar tu entreno o responder preguntas"
          />
        </form>
      )}

      {phase === "live" && (
        <>
          <form
            className="block"
            onSubmit={(event) => {
              event.preventDefault();
              send(text);
            }}
          >
            <ChatComposer
              placeholder={PLACEHOLDERS.live}
              value={text}
              onChange={setText}
              onSubmit={() => send(text)}
              disabled={busy}
              hint="Enter para añadir la serie"
            />
          </form>
          {entriesList}
          <div className="chat-actions">
            <button type="button" onClick={() => send("he terminado")} disabled={busy}>
              Terminar entreno
            </button>
          </div>
        </>
      )}

      {phase === "review" && draft && (
        <>
          <div className="block">
            <h2>Borrador</h2>
            <p className="subtitle">
              {translateDiscipline(draft.discipline)} · confianza{" "}
              {Math.round(draft.confidence * 100)}%
            </p>
            {draft.unresolved.length > 0 && (
              <p className="error">Sin resolver: {draft.unresolved.join(", ")}</p>
            )}
            {isCardio ? (
              <div className="profile-form">
                <label>
                  Duración (minutos)
                  <input
                    type="number"
                    min="1"
                    placeholder="Ej: 45"
                    value={durationMin}
                    onChange={(event) => setDurationMin(event.target.value)}
                  />
                </label>
                {DISTANCE_DISCIPLINES.includes(draft.discipline) && (
                  <label>
                    Distancia (km)
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder="Ej: 6.5"
                      value={distanceKm}
                      onChange={(event) => setDistanceKm(event.target.value)}
                    />
                  </label>
                )}
                <label>
                  Tipo de sesión
                  <select value={workoutType} onChange={(event) => setWorkoutType(event.target.value)}>
                    <option value="">— Sin especificar —</option>
                    {Object.entries(WORKOUT_TYPES).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            ) : (
              <table className="plain review-table">
              <thead>
                <tr>
                  <th>Ejercicio</th>
                  <th>Series</th>
                  <th>Reps</th>
                  <th>Peso (kg)</th>
                </tr>
              </thead>
              <tbody>
                {edits.map((exercise, index) => (
                  <tr key={`${index}-${exercise.name}`}>
                    <td>
                      <input
                        className="cell"
                        type="text"
                        value={exercise.name}
                        onChange={(event) => updateExercise(index, "name", event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="cell"
                        type="number"
                        min="1"
                        value={exercise.sets ?? ""}
                        onChange={(event) => updateExercise(index, "sets", event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="cell"
                        type="number"
                        min="1"
                        value={exercise.reps ?? ""}
                        onChange={(event) => updateExercise(index, "reps", event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        className="cell"
                        type="number"
                        min="0"
                        step="0.5"
                        value={exercise.weightKg ?? ""}
                        onChange={(event) => updateExercise(index, "weightKg", event.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            )}
          </div>

          <div className="block sliders">
            <label>
              Intensidad (RPE) · <strong>{rpe}</strong>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={rpe}
                onChange={(event) => setRpe(Number(event.target.value))}
              />
            </label>
            <label>
              Fatiga percibida · <strong>{fatigue}</strong>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={fatigue}
                onChange={(event) => setFatigue(Number(event.target.value))}
              />
            </label>
          </div>

          <div className="chat-actions">
            <button type="button" onClick={confirm} disabled={busy}>
              Confirmar
            </button>
            <button type="button" className="secondary" onClick={cancel} disabled={busy}>
              Cancelar
            </button>
          </div>
        </>
      )}

      {phase === "done" && session && (
        <>
          <section className="block">
            <h2>Sesión registrada</h2>
            <div className="stats">
              <div className="stat-card">
                <span className="stat-label">Volumen</span>
                <span className="stat-value">{Math.round(session.volumeKg)} kg</span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Calorías</span>
                <span className="stat-value">
                  {session.estimatedKcal != null ? `${Math.round(session.estimatedKcal)} kcal` : "—"}
                </span>
              </div>
              <div className="stat-card">
                <span className="stat-label">Duración</span>
                <span className="stat-value">
                  {session.durationMinutes ?? "—"} min
                </span>
              </div>
              {session.distanceMeters != null && (
                <div className="stat-card">
                  <span className="stat-label">Distancia</span>
                  <span className="stat-value">
                    {(session.distanceMeters / 1000).toFixed(1)} km
                  </span>
                </div>
              )}
              <div className="stat-card">
                <span className="stat-label">Ejercicios</span>
                <span className="stat-value">{session.exercises.length}</span>
              </div>
            </div>
            {session.details?.rpe != null && (
              <p className="subtitle">
                RPE {session.details.rpe}
                {session.details.perceivedFatigue != null
                  ? ` · Fatiga ${session.details.perceivedFatigue}`
                  : ""}
              </p>
            )}
            {session.muscleImpacts && session.muscleImpacts.length > 0 && (
              <div className="block">
                <h3>Músculos trabajados</h3>
                <BodyMap impacts={session.muscleImpacts} />
              </div>
            )}
          </section>
          <div className="chat-actions">
            <button type="button" onClick={reset}>
              Nuevo registro
            </button>
          </div>
        </>
      )}
    </main>
  );
}
