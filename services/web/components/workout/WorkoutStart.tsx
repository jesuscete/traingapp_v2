"use client";

import { useEffect, useState } from "react";
import { ClipboardList } from "lucide-react";

import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
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

  const suggested = gymDays.find((d) => d.dayOfWeek === todayDow) ?? gymDays[0] ?? null;
  const others = gymDays.filter((d) => d.id !== suggested?.id);

  return (
    <main className="dashboard">
      {pending > 0 && (
        <p className="wk-warn" role="status">
          {pending} entreno{pending === 1 ? "" : "s"} pendiente{pending === 1 ? "" : "s"} de
          enviar; se reintentará{pending === 1 ? "" : "n"} automáticamente.
        </p>
      )}

      <Card variant="raised" className="hoy-hero">
        <span className="hoy-hero-kicker">Entrenar</span>
        {loading && <Skeleton height={56} />}
        {!loading && suggested && (
          <>
            <h2>{suggested.label || WEEKDAYS[suggested.dayOfWeek - 1]}</h2>
            <p>
              {suggested.dayOfWeek === todayDow ? "Hoy" : WEEKDAYS[suggested.dayOfWeek - 1]} ·{" "}
              {suggested.exercises.length} ejercicios
            </p>
          </>
        )}
        {!loading && !suggested && <h2>¿Qué toca hoy?</h2>}
        {error && <p className="error">{error}</p>}
        <div className="hoy-hero-actions">
          {suggested ? (
            <Button size="lg" fullWidth onClick={() => startDay(suggested.id)}>
              Empezar entreno
            </Button>
          ) : (
            <Button size="lg" fullWidth onClick={() => onStart(newWorkout("Entreno libre", null, []))}>
              Entreno libre
            </Button>
          )}
        </div>
      </Card>
      <div className="wk-start-more">
        {others.length > 0 && <h3 className="wk-start-subtitle">Otros días de tu rutina</h3>}
        {others.length > 0 && (
          <div className="wk-days">
            {others.map((day) => (
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
            title="Crea tu primera rutina"
            text="Así verás aquí el día que toca."
            action={{ label: "Crear rutina", href: "/entrenar?tab=rutinas" }}
          />
        )}
        {!loading && routine && gymDays.length === 0 && (
          <p className="muted">Tu rutina activa no tiene días de gimnasio.</p>
        )}
        {sportDays.map((day) => (
          <p key={day.id} className="muted">
            {WEEKDAYS[day.dayOfWeek - 1]} · {DAY_TYPE_LABELS[day.dayType]}
            {day.disciplineName ? ` · ${translateDiscipline(day.disciplineName)}` : ""}
          </p>
        ))}
        {suggested && (
          <Button
            variant="text"
            fullWidth
            onClick={() => onStart(newWorkout("Entreno libre", null, []))}
          >
            O empieza un entreno libre (sin rutina)
          </Button>
        )}
      </div>
    </main>
  );
}
