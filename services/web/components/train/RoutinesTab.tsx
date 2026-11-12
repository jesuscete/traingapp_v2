"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ClipboardList } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { OverflowMenu } from "@/components/ui/OverflowMenu";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { RoutineEditor } from "@/components/rutinas/RoutineEditor";
import { RoutineAnalysis } from "@/components/rutinas/RoutineAnalysis";
import { RoutineReviewModal } from "@/components/rutinas/RoutineReviewModal";
import { DAY_TYPE_LABELS } from "@/lib/routines";
import type { Routine } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

export function RoutinesTab() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [active, setActive] = useState<Routine | null>(null);
  const [editing, setEditing] = useState<Routine | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [analyzing, setAnalyzing] = useState<Routine | null>(null);
  const [reviewing, setReviewing] = useState<Routine | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(
    async (authToken: string) => {
      try {
        const [list, activeRoutine] = await Promise.all([
          api.listRoutines(authToken),
          api.getActiveRoutine(authToken),
        ]);
        setRoutines(list);
        setActive(activeRoutine);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar rutinas");
      } finally {
        setLoaded(true);
      }
    },
    [],
  );

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    load(stored);
  }, [router, load]);

  async function activate(routine: Routine) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.updateRoutine(token, routine.id, { isActive: true });
      setActive(updated);
      setRoutines((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al activar la rutina");
    } finally {
      setBusy(false);
    }
  }

  async function duplicate(routine: Routine) {
    if (!token) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const copy = await api.duplicateRoutine(token, routine.id);
      await load(token);
      setNotice(`Rutina duplicada: "${copy.name}".`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al duplicar la rutina");
    } finally {
      setBusy(false);
    }
  }

  async function remove(routine: Routine) {
    if (!token) return;
    if (!window.confirm(`¿Eliminar la rutina "${routine.name}"?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteRoutine(token, routine.id);
      const list = routines.filter((item) => item.id !== routine.id);
      setRoutines(list);
      if (active?.id === routine.id) {
        setActive(null);
        setActive(await api.getActiveRoutine(token));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al borrar la rutina");
    } finally {
      setBusy(false);
    }
  }

  function handleSaved(saved: Routine) {
    setRoutines((prev) => {
      const exists = prev.some((item) => item.id === saved.id);
      return exists ? prev.map((item) => (item.id === saved.id ? saved : item)) : [...prev, saved];
    });
    setActive(saved);
    setEditing(null);
    setCreating(false);
  }

  if (!token) {
    return null;
  }

  if (creating || editing) {
    return (
      <div className="tab-body">
        <RoutineEditor
          token={token}
          routine={editing}
          onSaved={handleSaved}
          onCancel={() => {
            setEditing(null);
            setCreating(false);
          }}
        />
      </div>
    );
  }

  return (
    <div className="tab-body">
      {error && <p className="error">{error}</p>}
      {notice && <p className="ok">{notice}</p>}

      {!loaded && <Skeleton height={120} />}

      {loaded && routines.length === 0 && (
        <EmptyState
          icon={<ClipboardList size={28} strokeWidth={1.75} />}
          title="Crea tu primera rutina"
          text="Planifica tu semana de entrenos."
          action={{ label: "Crear rutina", onClick: () => setCreating(true) }}
        />
      )}

      {loaded && routines.length > 0 && (
        <>
          <section className="stats">
            {active ? (
              <div className="stat-card">
                <span className="stat-label">Rutina activa</span>
                <span className="stat-value">{active.name}</span>
                <span className="muted">
                  {active.days.length} día{active.days.length === 1 ? "" : "s"} a la semana
                </span>
              </div>
            ) : (
              <div className="stat-card">
                <span className="stat-label">Rutina activa</span>
                <span className="stat-value">Ninguna</span>
              </div>
            )}
          </section>

          <section className="block">
            {routines.map((routine) => (
              <div
                key={routine.id}
                className={routine.id === active?.id ? "routine-card active" : "routine-card"}
              >
                <div className="routine-card-header">
                  <strong>{routine.name}</strong>
                  {routine.id === active?.id && <span className="chips">Activa</span>}
                </div>
                <ul className="routine-days">
                  {routine.days.map((day) => (
                    <li key={day.dayOfWeek}>
                      <span className="muted">{DAY_TYPE_LABELS[day.dayType]}</span>
                      <span>{day.label || `Día ${day.dayOfWeek}`}</span>
                    </li>
                  ))}
                </ul>
                <div className="routine-card-actions">
                  <Button variant="secondary" onClick={() => setEditing(routine)}>
                    Editar
                  </Button>
                  <Button variant="secondary" onClick={() => setAnalyzing(routine)}>
                    Analizar
                  </Button>
                  <OverflowMenu
                    label={`Más acciones de ${routine.name}`}
                    items={[
                      ...(routine.id !== active?.id
                        ? [{ label: "Activar", onSelect: () => void activate(routine), disabled: busy }]
                        : []),
                      { label: "Evaluar", onSelect: () => setReviewing(routine) },
                      { label: "Duplicar", onSelect: () => void duplicate(routine), disabled: busy },
                      { label: "Borrar", onSelect: () => void remove(routine), danger: true, disabled: busy },
                    ]}
                  />
                </div>
              </div>
            ))}
            <div className="chat-actions">
              <button type="button" onClick={() => setCreating(true)}>
                + Nueva rutina
              </button>
            </div>
          </section>
        </>
      )}

      {analyzing && (
        <RoutineAnalysis
          token={token}
          routineId={analyzing.id}
          routineName={analyzing.name}
          onClose={() => setAnalyzing(null)}
        />
      )}

      {reviewing && (
        <RoutineReviewModal
          token={token}
          routineName={reviewing.name}
          days={reviewing.days}
          onClose={() => setReviewing(null)}
        />
      )}
    </div>
  );
}
