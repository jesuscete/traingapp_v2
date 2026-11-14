"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronRight, ClipboardList, Download, FilePenLine, Plus } from "lucide-react";

import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { ExternalWorkoutSheet } from "@/components/workout/ExternalWorkoutSheet";
import { WEEKDAYS } from "@/lib/routines";
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
  const [external, setExternal] = useState(false);
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

  // Solo días de gimnasio y sin «hoy toca»: el usuario elige qué entrena.
  const gymDays = (routine?.days ?? [])
    .filter((d) => d.dayType === "gimnasio")
    .sort((a, b) => a.dayOfWeek - b.dayOfWeek);

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

  const startFree = () => onStart(newWorkout("Entreno libre", null, []));

  return (
    <main className="dashboard wk-start">
      {pending > 0 && (
        <p className="wk-warn" role="status">
          {pending} entreno{pending === 1 ? "" : "s"} pendiente{pending === 1 ? "" : "s"} de
          enviar; se reintentará{pending === 1 ? "" : "n"} automáticamente.
        </p>
      )}

      <section className="wk-start-more">
        <div className="wk-start-head">
          <h3 className="wk-start-subtitle">Días de rutina</h3>
          <Link href="/rutinas" className="wk-start-link">
            Ver rutina <ChevronRight size={16} aria-hidden="true" />
          </Link>
        </div>
        {loading && <Skeleton height={120} />}
        {error && <p className="error">{error}</p>}
        {!loading && gymDays.length > 0 && (
          <div className="wk-days">
            {gymDays.map((day) => (
              <button key={day.id} type="button" className="wk-day" onClick={() => startDay(day.id)}>
                <span className="wk-day-top">
                  <strong>{day.label || WEEKDAYS[day.dayOfWeek - 1]}</strong>
                </span>
                <span className="muted">
                  {WEEKDAYS[day.dayOfWeek - 1]} · {day.exercises.length} ejercicios
                </span>
              </button>
            ))}
          </div>
        )}
        {!loading && !error && !routine && (
          <EmptyState
            icon={<ClipboardList size={28} strokeWidth={1.75} />}
            title="Aún no tienes rutina"
            text="Crea una para empezar cada día con un toque, o entrena libre."
            action={{ label: "Crear rutina", href: "/rutinas?tab=rutinas" }}
          />
        )}
        {!loading && routine && gymDays.length === 0 && (
          <p className="muted">Tu rutina activa no tiene días de gimnasio.</p>
        )}
      </section>

      <div className="wk-actions" role="group" aria-label="Otras formas de entrenar">
        <button type="button" className="wk-action" onClick={startFree}>
          <Plus size={22} strokeWidth={2} aria-hidden="true" />
          <span>Entreno libre</span>
        </button>
        <Link href="/registrar" className="wk-action">
          <FilePenLine size={22} strokeWidth={2} aria-hidden="true" />
          <span>Otra actividad</span>
        </Link>
        <button type="button" className="wk-action" onClick={() => setExternal(true)}>
          <Download size={22} strokeWidth={2} aria-hidden="true" />
          <span>Cargar entreno</span>
        </button>
      </div>

      {external && <ExternalWorkoutSheet token={token} onClose={() => setExternal(false)} />}
    </main>
  );
}
