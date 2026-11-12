"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { translateDiscipline } from "@/lib/labels";
import { DAY_TYPE_LABELS, WEEKDAYS } from "@/lib/routines";
import type { CatalogExercise, Routine } from "@/lib/types";
import { useCatalog } from "@/lib/useCatalog";
import {
  exercisesFromRoutineDay,
  newWorkout,
  routineDayTitle,
} from "@/lib/workout/ops";
import { loadPending } from "@/lib/workout/storage";
import type { ActiveWorkout } from "@/lib/workout/types";

export function WorkoutStart({
  token,
  onStart,
}: {
  token: string;
  onStart: (w: ActiveWorkout) => void;
}) {
  const [routine, setRoutine] = useState<Routine | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(0);
  const { catalog } = useCatalog(token);

  useEffect(() => {
    setPending(loadPending().length);
    let cancelled = false;
    api
      .getActiveRoutine(token)
      .then((r) => {
        if (!cancelled) setRoutine(r);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar tu rutina (puedes empezar un entreno vacío).");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  const gymDays = routine?.days.filter((d) => d.dayType === "gimnasio") ?? [];
  const sportDays = routine?.days.filter((d) => d.dayType === "deporte") ?? [];
  const todayDow = ((new Date().getDay() + 6) % 7) + 1;

  function startDay(dayId: string) {
    if (!routine) return;
    const day = routine.days.find((d) => d.id === dayId);
    if (!day) return;
    const list: CatalogExercise[] = catalog;
    onStart(
      newWorkout(
        routineDayTitle(routine, day, WEEKDAYS[day.dayOfWeek - 1]),
        day.id,
        exercisesFromRoutineDay(day, list),
      ),
    );
  }

  return (
    <main className="dashboard">
      <section className="welcome">
        <h2>Entrenar</h2>
        <p className="subtitle">Empieza un entreno vacío o sigue un día de tu rutina.</p>
      </section>

      {pending > 0 && (
        <p className="wk-warn" role="status">
          {pending} entreno{pending === 1 ? "" : "s"} pendiente{pending === 1 ? "" : "s"} de
          enviar; se reintentará{pending === 1 ? "" : "n"} automáticamente.
        </p>
      )}

      <button
        type="button"
        className="wk-primary wk-start-empty"
        onClick={() => onStart(newWorkout("Entreno libre", null, []))}
      >
        Entreno vacío
      </button>

      <Link className="imp-start-link" href="/importar">
        Importar actividad (.fit, .gpx, .tcx)
      </Link>

      <section className="block">
        <h2>Día de tu rutina</h2>
        {loading && <p className="muted">Cargando rutina…</p>}
        {error && <p className="error">{error}</p>}
        {!loading && !error && !routine && (
          <p className="muted">
            No tienes una rutina activa. <Link href="/rutinas">Crear una rutina</Link>
          </p>
        )}
        {!loading && routine && gymDays.length === 0 && (
          <p className="muted">Tu rutina activa no tiene días de gimnasio.</p>
        )}
        <div className="wk-days">
          {gymDays.map((day) => (
            <button
              key={day.id}
              type="button"
              className={`wk-day${day.dayOfWeek === todayDow ? " today" : ""}`}
              onClick={() => startDay(day.id)}
            >
              <span className="wk-day-top">
                <strong>{day.label || WEEKDAYS[day.dayOfWeek - 1]}</strong>
                {day.dayOfWeek === todayDow && <span className="wk-today-tag">Hoy</span>}
              </span>
              <span className="muted">
                {WEEKDAYS[day.dayOfWeek - 1]} · {day.exercises.length} ejercicios
              </span>
            </button>
          ))}
        </div>
      </section>

      <p>
        <Link className="back-link" href="/ejercicios">
          Biblioteca de ejercicios →
        </Link>
      </p>

      <section className="block">
        <h2>Otros deportes</h2>
        <p className="muted">
          Para boxeo, running, escalada u otras disciplinas usa el registro
          multideporte.
        </p>
        <p>
          <Link className="btn-secondary m3-link-btn" href="/registrar">
            Registrar actividad
          </Link>
        </p>
        <p className="muted">
          ¿Prefieres texto libre? Cuéntaselo al <Link href="/chat">chat</Link>.
        </p>
        {sportDays.map((day) => (
          <p key={day.id} className="muted">
            {WEEKDAYS[day.dayOfWeek - 1]} · {DAY_TYPE_LABELS[day.dayType]}
            {day.disciplineName ? ` · ${translateDiscipline(day.disciplineName)}` : ""}
          </p>
        ))}
      </section>
    </main>
  );
}
