"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
import { RoutineEditor } from "@/components/rutinas/RoutineEditor";
import { RoutineReviewModal } from "@/components/rutinas/RoutineReviewModal";
import { DAY_TYPE_LABELS } from "@/lib/routines";
import type { Routine } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

export default function Rutinas() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [active, setActive] = useState<Routine | null>(null);
  const [editing, setEditing] = useState<Routine | null>(null);
  const [creating, setCreating] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [reviewing, setReviewing] = useState<Routine | null>(null);

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
      <div className="dashboard">
        <RoutineEditor
          token={token}
          routine={editing}
          onSaved={handleSaved}
          onCancel={() => {
            setEditing(null);
            setCreating(false);
          }}
        />
        <BottomNav />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="topbar">
        <h1>Rutinas</h1>
      </div>

      {error && <p className="error">{error}</p>}

      {!loaded && <p className="muted">Cargando...</p>}

      {loaded && routines.length === 0 && (
        <section className="block">
          <p className="muted">
            Aún no tienes rutinas. Crea una semanal y planifica tus entrenos.
          </p>
          <div className="chat-actions">
            <button type="button" onClick={() => setCreating(true)}>
              Crear rutina
            </button>
          </div>
        </section>
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
                <div className="chat-actions">
                  {routine.id !== active?.id && (
                    <button type="button" className="secondary" disabled={busy} onClick={() => activate(routine)}>
                      Activar
                    </button>
                  )}
                  <button type="button" className="secondary" onClick={() => setEditing(routine)}>
                    Editar
                  </button>
                  <button type="button" className="secondary" onClick={() => setReviewing(routine)}>
                    Evaluar
                  </button>
                  <button type="button" className="link" disabled={busy} onClick={() => remove(routine)}>
                    Borrar
                  </button>
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

      {reviewing && (
        <RoutineReviewModal
          token={token}
          routineName={reviewing.name}
          days={reviewing.days}
          onClose={() => setReviewing(null)}
        />
      )}

      <BottomNav />
    </div>
  );
}
