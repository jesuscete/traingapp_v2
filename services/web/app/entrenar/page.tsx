"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
import {
  ExercisePickerModal,
  type PickerExercise,
} from "@/components/gym/ExercisePickerModal";
import { DAY_TYPE_LABELS, WEEKDAYS } from "@/lib/routines";
import { translateDiscipline } from "@/lib/labels";
import type {
  CatalogExercise,
  GymSession,
  LiveSession,
  Routine,
  Session,
} from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

type Phase = "loading" | "pick" | "live" | "done";

function numberOrNull(value: string): number | null {
  const parsed = Number(value);
  return value === "" || Number.isNaN(parsed) ? null : parsed;
}

function dayTitle(routine: Routine | null, dayId: string | null): string {
  if (!routine || !dayId) return "";
  const day = routine.days.find((item) => item.id === dayId);
  return day ? WEEKDAYS[day.dayOfWeek - 1] : "";
}

export default function Entrenar() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [routine, setRoutine] = useState<Routine | null>(null);
  const [live, setLive] = useState<LiveSession | null>(null);
  const [result, setResult] = useState<GymSession | Session | null>(null);
  const [draftValues, setDraftValues] = useState<Record<string, string>>({});
  const [catalog, setCatalog] = useState<CatalogExercise[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [durationMin, setDurationMin] = useState("");
  const [intensity, setIntensity] = useState(7);
  const [fatigue, setFatigue] = useState(5);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    (async () => {
      try {
        const existing = await api.getLive(stored);
        if (existing) {
          setLive(existing);
          setPhase("live");
        } else {
          const activeRoutine = await api.getActiveRoutine(stored);
          setRoutine(activeRoutine);
          setPhase("pick");
        }
      } catch {
        setError("No se pudo conectar con el servidor.");
        setPhase("pick");
      }
    })();
  }, [router]);

  useEffect(() => {
    if (phase === "live" && live && token) {
      api.listCatalogExercises(token).then(setCatalog).catch(() => setCatalog([]));
    }
  }, [phase, live, token]);

  useEffect(() => {
    if (!live) return;
    const next: Record<string, string> = {};
    live.exercises.forEach((exercise, exerciseIndex) => {
      exercise.sets.forEach((workoutSet) => {
        next[`${exerciseIndex}-${workoutSet.setNumber}`] = `${
          workoutSet.weight ?? ""
        }|${workoutSet.reps ?? ""}`;
      });
    });
    setDraftValues(next);
  }, [live]);

  async function start(routineDayId: string | null) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const session = await api.startLive(token, routineDayId);
      setLive(session);
      setPhase("live");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al iniciar la sesión");
    } finally {
      setBusy(false);
    }
  }

  async function commitSet(exerciseIndex: number, setNumber: number, value: string) {
    if (!token) return;
    const [weightRaw, repsRaw] = value.split("|");
    const weight = numberOrNull(weightRaw);
    const reps = numberOrNull(repsRaw);
    const isClean =
      weight === null && reps === null && (weightRaw === "" || repsRaw === "");
    if (isClean) return;
    try {
      const updated = await api.patchLiveSet(token, {
        exerciseIndex,
        setNumber,
        weight,
        reps,
      });
      setLive(updated);
    } catch {
      // Ignora el error; el siguiente blur reintentará
    }
  }

  async function addPickerExercises(exercises: PickerExercise[]) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      let updated = live;
      for (const exercise of exercises) {
        updated = await api.addLiveExercise(token, {
          name: exercise.name,
          exerciseId: exercise.exerciseId,
          sets: exercise.sets.map((workoutSet) => ({
            setNumber: workoutSet.setNumber,
            weight: workoutSet.weightKg,
            reps: workoutSet.reps,
          })),
        });
      }
      setLive(updated);
      setPickerOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al añadir ejercicio");
    } finally {
      setBusy(false);
    }
  }

  async function addSet(exerciseIndex: number) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const current = live?.exercises[exerciseIndex];
      const nextNumber = (current?.sets.length ?? 0) + 1;
      const updated = await api.addLiveSet(token, exerciseIndex, {
        setNumber: nextNumber,
        weight: null,
        reps: null,
      });
      setLive(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al añadir serie");
    } finally {
      setBusy(false);
    }
  }

  async function finish() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const saved = await api.finishLive(token, {
        durationMinutes: durationMin !== "" ? Number(durationMin) : null,
        intensity,
        fatigue,
        note: note.trim() || null,
      });
      setResult(saved);
      setPhase("done");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Error al terminar la sesión. Pon peso a las series.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!token) return;
    if (!window.confirm("¿Descartar la sesión en curso?")) return;
    setBusy(true);
    setError(null);
    try {
      await api.cancelLive(token);
      setLive(null);
      setPhase("pick");
      setRoutine(await api.getActiveRoutine(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cancelar");
    } finally {
      setBusy(false);
    }
  }

  if (!token || phase === "loading") {
    return (
      <main className="dashboard">
        <BottomNav />
        <p className="muted">Cargando...</p>
      </main>
    );
  }

  if (phase === "done" && result) {
    const isGym = "workoutExercises" in result;
    return (
      <main className="dashboard">
        <div className="welcome">
          <h2>Sesión registrada</h2>
          <p className="subtitle">
            {isGym
              ? `${result.workoutExercises.length} ejercicios, ${result.volumeKg.toFixed(0)} kg de volumen.`
              : `${translateDiscipline(result.discipline)} · ${result.volumeKg.toFixed(0)} kg.`}
          </p>
        </div>
        <section className="block">
          <div className="chat-actions">
            <button type="button" onClick={() => router.push("/entrenos")}>
              Ver historial
            </button>
            <button type="button" className="secondary" onClick={() => router.push("/dashboard")}>
              Inicio
            </button>
          </div>
        </section>
        <BottomNav />
      </main>
    );
  }

  if (phase === "pick") {
    const gymDays =
      routine?.days.filter((day) => day.dayType === "gimnasio") ?? [];
    const sportDays =
      routine?.days.filter((day) => day.dayType === "deporte") ?? [];
    return (
      <main className="dashboard">
        <div className="welcome">
          <h2>Entrenar</h2>
          <p className="subtitle">
            Elige el día de tu rutina o empieza una sesión libre.
          </p>
        </div>

        {error && <p className="error">{error}</p>}

        <section className="block">
          <h2>Día de la rutina</h2>
          {!routine && <p className="muted">No tienes una rutina activa.</p>}
          {gymDays.length === 0 && sportDays.length === 0 && routine && (
            <p className="muted">Tu rutina activa no tiene días de entreno.</p>
          )}
          {[...gymDays, ...sportDays].map((day) => (
            <div key={day.id} className="routine-card">
              <div className="routine-card-header">
                <strong>{day.label || WEEKDAYS[day.dayOfWeek - 1]}</strong>
                <span className="chips">{DAY_TYPE_LABELS[day.dayType]}</span>
              </div>
              {day.dayType === "deporte" && (
                <p className="muted">
                  {day.disciplineName
                    ? translateDiscipline(day.disciplineName)
                    : "Actividad"}
                  {day.targetDurationMin != null
                    ? ` · ${day.targetDurationMin} min`
                    : ""}
                </p>
              )}
              <div className="chat-actions">
                <button type="button" disabled={busy} onClick={() => start(day.id)}>
                  Iniciar
                </button>
              </div>
            </div>
          ))}
          <div className="chat-actions">
            <button type="button" className="secondary" disabled={busy} onClick={() => start(null)}>
              Sesión libre
            </button>
          </div>
        </section>

        <BottomNav />
      </main>
    );
  }

  const titleDay = dayTitle(routine, live?.routineDayId ?? null);

  return (
    <main className="dashboard">
      <div className="welcome">
        <h2>
          {live?.origin === "routine"
            ? `Sesión: ${titleDay || "Rutina"}`
            : "Sesión libre"}
        </h2>
        <p className="subtitle">
          {live?.discipline === "gym"
            ? "Gimnasio"
            : live?.discipline
              ? translateDiscipline(live.discipline)
              : "Sin disciplina"}
          {live ? ` · ${live.entriesCount} anotación${live.entriesCount === 1 ? "" : "es"}` : ""}
        </p>
      </div>

      {error && <p className="error">{error}</p>}

      <section className="block">
        <h2>Ejercicios</h2>
        {live && live.exercises.length === 0 && (
          <p className="muted">
            Añade un ejercicio buscándolo en el catálogo, o registra la sesión desde el chat.
          </p>
        )}
        {live?.exercises.map((exercise, exerciseIndex) => (
          <div key={`${exercise.exerciseId ?? exercise.name}-${exerciseIndex}`} className="routine-exercise">
            <div className="routine-exercise-header">
              <strong>{exercise.name}</strong>
            </div>
            <table className="plain review-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Peso</th>
                  <th>Reps</th>
                  <th>Sug.</th>
                </tr>
              </thead>
              <tbody>
                {exercise.sets.map((workoutSet) => {
                  const key = `${exerciseIndex}-${workoutSet.setNumber}`;
                  const current = draftValues[key] ?? "|";
                  const [weightRaw, repsRaw] = current.split("|");
                  return (
                    <tr key={workoutSet.setNumber}>
                      <td className="muted">{workoutSet.setNumber}</td>
                      <td>
                        <input
                          className="cell"
                          type="number"
                          min="0"
                          step="0.5"
                          placeholder={
                            workoutSet.suggestedWeight != null
                              ? String(workoutSet.suggestedWeight)
                              : ""
                          }
                          value={weightRaw}
                          onChange={(event) =>
                            setDraftValues((prev) => ({
                              ...prev,
                              [key]: `${event.target.value}|${repsRaw}`,
                            }))
                          }
                          onBlur={() => commitSet(exerciseIndex, workoutSet.setNumber, current)}
                        />
                      </td>
                      <td>
                        <input
                          className="cell"
                          type="number"
                          min="0"
                          placeholder={
                            workoutSet.targetRepsMin != null
                              ? String(workoutSet.targetRepsMin)
                              : ""
                          }
                          value={repsRaw}
                          onChange={(event) =>
                            setDraftValues((prev) => ({
                              ...prev,
                              [key]: `${weightRaw}|${event.target.value}`,
                            }))
                          }
                          onBlur={() => commitSet(exerciseIndex, workoutSet.setNumber, current)}
                        />
                      </td>
                      <td className="muted">
                        {workoutSet.suggestedWeight != null
                          ? `${workoutSet.suggestedWeight} kg`
                          : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="routine-exercise-actions">
              <button type="button" className="link" disabled={busy} onClick={() => addSet(exerciseIndex)}>
                + Serie
              </button>
            </div>
          </div>
        ))}

        <div className="chat-actions">
          <button type="button" disabled={busy} onClick={() => setPickerOpen(true)}>
            + Añadir ejercicio
          </button>
        </div>
      </section>

      <section className="block">
        <h2>Terminar sesión</h2>
        <div className="profile-form">
          <label>
            Duración (min)
            <input
              type="number"
              min="1"
              value={durationMin}
              onChange={(event) => setDurationMin(event.target.value)}
            />
          </label>
        </div>
        <div className="sliders">
          <label>
            Intensidad percibida: {intensity}/10
            <input
              type="range"
              min="0"
              max="10"
              value={intensity}
              onChange={(event) => setIntensity(Number(event.target.value))}
            />
          </label>
          <label>
            Fatiga: {fatigue}/10
            <input
              type="range"
              min="0"
              max="10"
              value={fatigue}
              onChange={(event) => setFatigue(Number(event.target.value))}
            />
          </label>
        </div>
        <div className="profile-form">
          <label>
            Nota
            <input
              type="text"
              maxLength={500}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
          </label>
        </div>
        <div className="chat-actions">
          <button type="button" onClick={finish} disabled={busy}>
            Guardar sesión
          </button>
          <button type="button" className="link" onClick={cancel} disabled={busy}>
            Descartar
          </button>
        </div>
      </section>

      {pickerOpen && (
        <ExercisePickerModal
          catalog={catalog}
          lockedIds={live?.exercises
            .map((exercise) => exercise.exerciseId)
            .filter((id): id is string => id != null)}
          onSave={addPickerExercises}
          onCancel={() => setPickerOpen(false)}
        />
      )}

      <BottomNav />
    </main>
  );
}
