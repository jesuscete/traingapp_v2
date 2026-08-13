"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { DAY_TYPE_LABELS, DAY_TYPE_OPTIONS, WEEKDAYS } from "@/lib/routines";
import { DisciplinePicker } from "@/components/rutinas/DisciplinePicker";
import { RoutineReviewModal } from "@/components/rutinas/RoutineReviewModal";
import {
  ExercisePickerModal,
  type PickerExercise,
} from "@/components/gym/ExercisePickerModal";
import type {
  CatalogExercise,
  DayType,
  Discipline,
  Routine,
  RoutineDay,
  RoutineDayInput,
} from "@/lib/types";

type DraftSet = {
  setNumber: number;
  targetRepsMin: number | null;
  targetWeightKg: number | null;
};

type DraftExercise = {
  exerciseId: string;
  name: string;
  sets: DraftSet[];
};

type DraftDay = {
  dayOfWeek: number;
  dayType: DayType;
  label: string;
  disciplineId: string;
  targetDurationMin: string;
  exercises: DraftExercise[];
};

function toDraftDay(day: RoutineDay): DraftDay {
  return {
    dayOfWeek: day.dayOfWeek,
    dayType: day.dayType,
    label: day.label ?? "",
    disciplineId: day.disciplineId ?? "",
    targetDurationMin:
      day.targetDurationMin != null ? String(day.targetDurationMin) : "",
    exercises: day.exercises.map((exercise) => ({
      exerciseId: exercise.exerciseId ?? "",
      name: exercise.name ?? "",
      sets: exercise.sets.map((workoutSet) => ({
        setNumber: workoutSet.setNumber,
        targetRepsMin: workoutSet.targetRepsMin,
        targetWeightKg: null,
      })),
    })),
  };
}

function emptyDay(dayOfWeek: number): DraftDay {
  return {
    dayOfWeek,
    dayType: "gimnasio",
    label: "",
    disciplineId: "",
    targetDurationMin: "",
    exercises: [],
  };
}

function dayToInput(day: DraftDay): RoutineDayInput {
  const isGym = day.dayType === "gimnasio";
  const isSport = day.dayType === "deporte";
  return {
    dayOfWeek: day.dayOfWeek,
    dayType: day.dayType,
    label: day.label.trim() || null,
    disciplineId: isSport && day.disciplineId ? day.disciplineId : null,
    targetDurationMin:
      isSport && day.targetDurationMin !== ""
        ? Number(day.targetDurationMin)
        : null,
    notes: null,
    exercises: isGym
      ? day.exercises.map((exercise, index) => ({
          exerciseId: exercise.exerciseId,
          orderIndex: index,
          supersetGroupId: null,
          sets: exercise.sets.map((workoutSet) => ({
            setNumber: workoutSet.setNumber,
            setType: "normal",
            targetRepsMin: workoutSet.targetRepsMin,
            targetRepsMax: null,
            targetRestSeconds: null,
          })),
        }))
      : [],
  };
}

type Props = {
  token: string;
  routine: Routine | null;
  onSaved: (routine: Routine) => void;
  onCancel: () => void;
};

export function RoutineEditor({ token, routine, onSaved, onCancel }: Props) {
  const [name, setName] = useState(routine?.name ?? "");
  const [days, setDays] = useState<DraftDay[]>(
    routine?.days.length ? routine.days.map(toDraftDay) : [emptyDay(1)],
  );
  const [catalog, setCatalog] = useState<CatalogExercise[]>([]);
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [pickerDay, setPickerDay] = useState<number | null>(null);
  const [collapsedDays, setCollapsedDays] = useState<Set<number>>(
    () =>
      new Set(
        (routine?.days ?? [])
          .filter((day) => day.exercises.length > 0)
          .map((day) => day.dayOfWeek),
      ),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);

  useEffect(() => {
    api.listCatalogExercises(token).then(setCatalog).catch(() => setCatalog([]));
    api.listDisciplines(token).then(setDisciplines).catch(() => setDisciplines([]));
  }, [token]);

  function updateDay(index: number, patch: Partial<DraftDay>) {
    setDays((prev) => prev.map((day, i) => (i === index ? { ...day, ...patch } : day)));
  }

  function applyPicker(dayIndex: number, exercises: PickerExercise[]) {
    updateDay(dayIndex, {
      exercises: exercises.map((item) => ({
        exerciseId: item.exerciseId,
        name: item.name,
        sets: item.sets.map((workoutSet) => ({
          setNumber: workoutSet.setNumber,
          targetRepsMin: workoutSet.reps,
          targetWeightKg: workoutSet.weightKg,
        })),
      })),
    });
    setPickerDay(null);
  }

  function addDay() {
    setDays((prev) => {
      const used = new Set(prev.map((day) => day.dayOfWeek));
      const next = [1, 2, 3, 4, 5, 6, 7].find((dow) => !used.has(dow));
      return next != null ? [...prev, emptyDay(next)] : prev;
    });
  }

  function removeDay(index: number) {
    setDays((prev) => (prev.length > 1 ? prev.filter((_, i) => i !== index) : prev));
  }

  function toggleDay(dayOfWeek: number) {
    setCollapsedDays((prev) => {
      const next = new Set(prev);
      if (next.has(dayOfWeek)) next.delete(dayOfWeek);
      else next.add(dayOfWeek);
      return next;
    });
  }

  async function save() {
    if (!name.trim()) {
      setError("Ponle un nombre a la rutina.");
      return;
    }
    for (const day of days) {
      if (day.dayType === "gimnasio" && day.exercises.length === 0) {
        setError(`El día ${WEEKDAYS[day.dayOfWeek - 1]} necesita al menos un ejercicio.`);
        return;
      }
      if (day.dayType === "deporte" && !day.disciplineId) {
        setError(`El día ${WEEKDAYS[day.dayOfWeek - 1]} necesita una disciplina.`);
        return;
      }
    }
    setBusy(true);
    setError(null);
    try {
      let updated = routine;
      if (routine) {
        await api.updateRoutine(token, routine.id, { name: name.trim() });
        const existing = new Set(routine.days.map((day) => day.dayOfWeek));
        for (const day of days) {
          updated = await api.upsertRoutineDay(
            token,
            routine.id,
            day.dayOfWeek,
            dayToInput(day),
          );
        }
        for (const dow of existing) {
          if (!days.some((day) => day.dayOfWeek === dow)) {
            updated = await api.deleteRoutineDay(token, routine.id, dow);
          }
        }
      } else {
        updated = await api.createRoutine(token, {
          name: name.trim(),
          days: days.map(dayToInput),
        });
      }
      if (updated) onSaved(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar la rutina");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="block">
      <div className="topbar">
        <h2>{routine ? "Editar rutina" : "Nueva rutina"}</h2>
        <button type="button" className="link" onClick={onCancel}>
          Volver
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      <div className="profile-form">
        <label>
          Nombre de la rutina
          <input
            type="text"
            maxLength={120}
            placeholder="Ej: Rutina A"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
      </div>

      {days.map((day, dayIndex) => {
        const collapsed = collapsedDays.has(day.dayOfWeek);
        const dayTitle = day.label.trim() || WEEKDAYS[day.dayOfWeek - 1];
        const exerciseCount = day.exercises.length;
        return (
          <div
            key={day.dayOfWeek}
            className={`routine-day${collapsed ? " collapsed" : ""}`}
          >
            <div className="routine-day-header">
              <button
                type="button"
                className="routine-day-toggle"
                onClick={() => toggleDay(day.dayOfWeek)}
              >
                <span className={`routine-day-chevron${collapsed ? "" : " open"}`}>
                  ▸
                </span>
                <strong>{dayTitle}</strong>
                {exerciseCount > 0 && (
                  <span className="muted">
                    {exerciseCount} {exerciseCount === 1 ? "ejercicio" : "ejercicios"}
                  </span>
                )}
              </button>
              <select
                value={day.dayOfWeek}
                onChange={(event) =>
                  updateDay(dayIndex, { dayOfWeek: Number(event.target.value) })
                }
              >
                {[1, 2, 3, 4, 5, 6, 7].map((dow) => (
                  <option key={dow} value={dow}>
                    {WEEKDAYS[dow - 1]}
                  </option>
                ))}
              </select>
              <select
                value={day.dayType}
                onChange={(event) =>
                  updateDay(dayIndex, { dayType: event.target.value as DayType })
                }
              >
                {DAY_TYPE_OPTIONS.map((type) => (
                  <option key={type} value={type}>
                    {DAY_TYPE_LABELS[type]}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className="link"
                onClick={() => removeDay(dayIndex)}
                disabled={days.length <= 1}
              >
                Quitar
              </button>
            </div>

          {!collapsed && (
          <>
          <div className="profile-form">
            <label>
              Etiqueta (opcional)
              <input
                type="text"
                maxLength={80}
                placeholder="Ej: Día de empuje"
                value={day.label}
                onChange={(event) => updateDay(dayIndex, { label: event.target.value })}
              />
            </label>
          </div>

          {day.dayType === "deporte" && (
            <div className="profile-form">
              <label>
                Disciplina
                <DisciplinePicker
                  disciplines={disciplines}
                  value={day.disciplineId ?? ""}
                  onChange={(disciplineId) =>
                    updateDay(dayIndex, { disciplineId })
                  }
                />
              </label>
              <label>
                Duración objetivo (min)
                <input
                  type="number"
                  min="1"
                  placeholder="Ej: 45"
                  value={day.targetDurationMin}
                  onChange={(event) =>
                    updateDay(dayIndex, { targetDurationMin: event.target.value })
                  }
                />
              </label>
            </div>
          )}

          {day.dayType === "gimnasio" && (
            <>
              <div className="chat-actions">
                <button type="button" onClick={() => setPickerDay(dayIndex)}>
                  + Añadir ejercicio
                </button>
              </div>
              {day.exercises.length === 0 && (
                <p className="muted">
                  Este día aún no tiene ejercicios. Pulsa "Añadir ejercicio" para configurarlos.
                </p>
              )}
              {day.exercises.map((exercise) => (
                <div key={exercise.exerciseId} className="routine-exercise">
                  <div className="routine-exercise-header">
                    <strong>{exercise.name}</strong>
                    <span className="muted">
                      {exercise.sets.length} {exercise.sets.length === 1 ? "serie" : "series"}
                    </span>
                  </div>
                  <table className="plain routine-sets">
                    <thead>
                      <tr>
                        <th>Serie</th>
                        <th>Reps</th>
                        <th>Peso (kg)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {exercise.sets.map((workoutSet) => (
                        <tr key={workoutSet.setNumber}>
                          <td>{workoutSet.setNumber}</td>
                          <td>{workoutSet.targetRepsMin ?? "—"}</td>
                          <td>{workoutSet.targetWeightKg ?? "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ))}
            </>
          )}

          {day.dayType === "descanso" && (
            <p className="muted">Día de descanso: sin ejercicios.</p>
          )}
          </>
          )}
          </div>
        );
      })}

      <div className="chat-actions">
        <button
          type="button"
          className="secondary"
          onClick={() => setReviewOpen(true)}
        >
          Evaluar rutina
        </button>
        <button type="button" className="secondary" onClick={addDay}>
          + Añadir día
        </button>
        <button type="button" onClick={save} disabled={busy}>
          Guardar rutina
        </button>
      </div>

      {pickerDay != null && (
        <ExercisePickerModal
          catalog={catalog}
          title={routine ? "Editar día" : "Añadir ejercicio"}
          initial={
            days[pickerDay]?.exercises.map((exercise) => ({
              exerciseId: exercise.exerciseId,
              name: exercise.name,
              sets: exercise.sets.map((workoutSet) => ({
                setNumber: workoutSet.setNumber,
                reps: workoutSet.targetRepsMin,
                weightKg: workoutSet.targetWeightKg,
              })),
            })) ?? []
          }
          onSave={(exercises) => applyPicker(pickerDay, exercises)}
          onCancel={() => setPickerDay(null)}
        />
      )}

      {reviewOpen && (
        <RoutineReviewModal
          token={token}
          routineName={name.trim() || routine?.name}
          days={days}
          catalog={catalog}
          disciplines={disciplines}
          onClose={() => setReviewOpen(false)}
        />
      )}
    </section>
  );
}