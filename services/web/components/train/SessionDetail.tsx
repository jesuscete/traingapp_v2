"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { ActivitySection } from "@/components/activity/ActivitySection";
import { ActivityStats } from "@/components/activity/ActivityStats";
import { ProgressPlaceholder } from "@/components/activity/ProgressPlaceholder";
import {
  ActivityForm,
  toLocalInput,
  type ActivitySubmit,
  type ActivityValues,
} from "@/components/metrics/ActivityForm";
import { MetricsView } from "@/components/metrics/MetricsView";
import { CaloriesCard } from "@/components/gym/CaloriesCard";
import { ExerciseSessionStats } from "@/components/gym/ExerciseSessionStats";
import { MuscleFatigue } from "@/components/gym/MuscleFatigue";
import { VolumeBreakdown } from "@/components/gym/VolumeBreakdown";
import { Skeleton } from "@/components/ui/Skeleton";
import { api } from "@/lib/api";
import { translateDiscipline } from "@/lib/labels";
import { formToMetrics, metricsKindFor, metricsToForm } from "@/lib/metrics";
import type { GymSession, Session, SessionUpdate } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

function isGymSession(session: Session | GymSession): session is GymSession {
  return "workoutExercises" in session;
}

export function SessionDetail({ id, embedded = false }: { id: string; embedded?: boolean }) {
  const router = useRouter();
  const params = { id };
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | GymSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    load(stored, params.id);
  }, [router, params.id]);

  const load = useCallback(async (accessToken: string, id: string) => {
    setLoading(true);
    try {
      const s = await api.getSession(accessToken, id);
      setSession(s);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el entreno");
    } finally {
      setLoading(false);
    }
  }, []);

  const isGym = session != null && isGymSession(session);
  const metrics = session?.details?.metrics ?? null;

  async function save(data: ActivitySubmit) {
    if (!token || !session) return;
    const body: SessionUpdate = {};
    if (new Date(data.performedAtIso).getTime() !== new Date(session.performedAt).getTime()) {
      body.performedAt = data.performedAtIso;
    }
    if (data.durationMinutes != null && data.durationMinutes !== session.durationMinutes) {
      body.durationMinutes = data.durationMinutes;
    }
    if (data.intensity != null && data.intensity !== session.intensity) {
      body.intensity = data.intensity;
    }
    if (data.note !== (session.note ?? "")) body.note = data.note;
    if (!isGym && metrics && data.metrics) {
      const original = formToMetrics(metricsKindFor(session.discipline), metricsToForm(metrics));
      if (JSON.stringify(original.metrics) !== JSON.stringify(data.metrics)) {
        body.metrics = data.metrics;
      }
    }
    if (Object.keys(body).length === 0) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await api.updateSession(token, session.id, body);
      await load(token, session.id);
      setEditing(false);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  function editInitial(current: Session | GymSession): ActivityValues {
    return {
      performedAt: toLocalInput(current.performedAt),
      durationMinutes: current.durationMinutes != null ? String(current.durationMinutes) : "",
      intensity: current.intensity ?? null,
      note: current.note ?? "",
      metricsForm: metricsToForm(current.details?.metrics),
    };
  }

  return (
    <div className="detail-pane">
      {!embedded && (
        <p>
          <Link className="back-link" href="/entrenar?tab=historial">
            ← Volver a Entrenos
          </Link>
        </p>
      )}

      {loading ? (
        <div className="detail-skeleton"><Skeleton height={32} width="50%" /><Skeleton height={120} /><Skeleton height={200} /></div>
      ) : error ? (
        <p className="error">
          {error}{" "}
          <button type="button" className="ui-btn text" onClick={() => token && void load(token, id)}>Reintentar</button>
        </p>
      ) : session ? (
        <>
          <section className="welcome">
            <h2>{translateDiscipline(session.discipline)}</h2>
            <p className="subtitle">
              {new Date(session.performedAt).toLocaleDateString()} ·{" "}
              {session.durationMinutes != null
                ? `${session.durationMinutes} min`
                : "duración no registrada"}
            </p>
            {session.discipline === "gym" && !editing && (
              <p>
                <Link href="/progreso?tab=rendimiento">Analizar mi preparación</Link>
              </p>
            )}
            {!editing && (
              <button
                type="button"
                className="secondary m3-edit-btn"
                onClick={() => {
                  setSaveError(null);
                  setEditing(true);
                }}
              >
                Editar
              </button>
            )}
          </section>

          {editing ? (
            <ActivityForm
              discipline={session.discipline}
              headerOnly={isGym || !metrics}
              initial={editInitial(session)}
              submitLabel="Guardar cambios"
              busy={saving}
              error={saveError}
              onSubmit={(data) => void save(data)}
              onCancel={() => setEditing(false)}
            />
          ) : isGym ? (
            <>
              <ExerciseSessionStats exercises={session.workoutExercises} />
              {token && (
                <ActivitySection
                  token={token}
                  sessionId={session.id}
                  discipline={session.discipline}
                />
              )}
              <VolumeBreakdown session={session} />
              <CaloriesCard session={session} />
              <MuscleFatigue impacts={session.muscleImpacts} />
            </>
          ) : (
            <>
              <ActivityStats session={session} />
              {metrics && (
                <MetricsView
                  metrics={metrics}
                  discipline={session.discipline}
                  durationMinutes={session.durationMinutes}
                />
              )}
              {token && (
                <ActivitySection
                  token={token}
                  sessionId={session.id}
                  discipline={session.discipline}
                />
              )}
              <MuscleFatigue impacts={session.muscleImpacts ?? []} />
              <CaloriesCard session={session} />

              {(session.intensity != null || session.fatigue != null) && (
                <section className="block">
                  <h2>Esfuerzo percibido</h2>
                  <div className="bars">
                    {session.intensity != null && (
                      <div className="bar-row">
                        <span className="bar-label">
                          Intensidad · {session.intensity}/10
                        </span>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${session.intensity * 10}%` }}
                          />
                        </div>
                      </div>
                    )}
                    {session.fatigue != null && (
                      <div className="bar-row">
                        <span className="bar-label">
                          Fatiga · {session.fatigue}/10
                        </span>
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{ width: `${session.fatigue * 10}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}

              {session.note && (
                <section className="block">
                  <h2>Nota</h2>
                  <p>{session.note}</p>
                </section>
              )}

              <section className="block">
                <h2>Detalle</h2>
                <p className="muted">{session.rawText}</p>
              </section>

              {session.exercises.length > 0 && (
                <section className="block">
                  <h2>Ejercicios</h2>
                  <table className="plain">
                    <thead>
                      <tr>
                        <th>Ejercicio</th>
                        <th>Series</th>
                        <th>Reps</th>
                        <th>Peso</th>
                        <th>Duración</th>
                        <th>Distancia</th>
                        <th>Volumen</th>
                      </tr>
                    </thead>
                    <tbody>
                      {session.exercises.map((ex) => (
                        <tr key={ex.id}>
                          <td>{ex.name}</td>
                          <td>{ex.sets ?? "—"}</td>
                          <td>{ex.reps ?? "—"}</td>
                          <td>
                            {ex.weightKg != null ? `${ex.weightKg} kg` : "—"}
                          </td>
                          <td>
                            {ex.durationMinutes != null
                              ? `${ex.durationMinutes} min`
                              : "—"}
                          </td>
                          <td>
                            {ex.distanceMeters != null
                              ? `${ex.distanceMeters} m`
                              : "—"}
                          </td>
                          <td>{Math.round(ex.volumeKg)} kg</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </section>
              )}

              <ProgressPlaceholder session={session} />
            </>
          )}
        </>
      ) : null}
    </div>
  );
}
