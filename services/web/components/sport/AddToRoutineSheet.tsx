"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Routine, SportSuggestion } from "@/lib/types";

const WEEKDAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

type Props = {
  token: string;
  suggestion: SportSuggestion;
  onClose: () => void;
  onAdded: (message: string) => void;
};

export function AddToRoutineSheet({ token, suggestion, onClose, onAdded }: Props) {
  const [routine, setRoutine] = useState<Routine | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [busyDay, setBusyDay] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getActiveRoutine(token)
      .then((r) => {
        if (!cancelled) setRoutine(r);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setRoutine(null);
          setError(err instanceof Error ? err.message : "No se pudo cargar la rutina");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  async function add(dayOfWeek: number) {
    if (!routine || busyDay !== null) return;
    setBusyDay(dayOfWeek);
    setError(null);
    try {
      await api.addRoutineDayExercise(token, routine.id, dayOfWeek, {
        exerciseId: suggestion.exerciseId,
      });
      onAdded(`«${suggestion.name}» añadido al ${WEEKDAYS[dayOfWeek - 1].toLowerCase()}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo añadir el ejercicio");
    } finally {
      setBusyDay(null);
    }
  }

  const gymDays = routine?.days.filter((d) => d.dayType === "gimnasio") ?? [];

  return (
    <div
      className="sheet-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label="Añadir a la rutina"
      onClick={onClose}
    >
      <div className="sheet m3-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h3>Añadir a la rutina</h3>
          <button type="button" className="sheet-close" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="sheet-body">
          <p className="m4-sheet-ex">{suggestion.name}</p>
          {routine === undefined ? (
            <p className="muted">Cargando rutina…</p>
          ) : routine === null ? (
            <p className="muted">No tienes una rutina activa. Crea o activa una en Rutinas.</p>
          ) : gymDays.length === 0 ? (
            <p className="muted">
              Tu rutina «{routine.name}» no tiene días de gimnasio donde añadirlo.
            </p>
          ) : (
            <>
              <p className="muted">Elige el día de «{routine.name}»:</p>
              <div className="m4-day-list">
                {gymDays.map((day) => (
                  <button
                    key={day.id}
                    type="button"
                    className="m4-day-btn"
                    disabled={busyDay !== null}
                    onClick={() => void add(day.dayOfWeek)}
                  >
                    <strong>{WEEKDAYS[day.dayOfWeek - 1]}</strong>
                    <span className="muted">
                      {day.label ? `${day.label} · ` : ""}
                      {day.exercises.length} ejercicios
                    </span>
                    {busyDay === day.dayOfWeek && <span className="muted">Añadiendo…</span>}
                  </button>
                ))}
              </div>
            </>
          )}
          {error && <p className="error">{error}</p>}
        </div>
      </div>
    </div>
  );
}
