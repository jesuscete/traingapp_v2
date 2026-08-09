"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { ActivityStats } from "@/components/activity/ActivityStats";
import { ProgressPlaceholder } from "@/components/activity/ProgressPlaceholder";
import { CaloriesCard } from "@/components/gym/CaloriesCard";
import { ExerciseRoutine } from "@/components/gym/ExerciseRoutine";
import { ExerciseStatsPlaceholder } from "@/components/gym/ExerciseStatsPlaceholder";
import { MuscleFatigue } from "@/components/gym/MuscleFatigue";
import { VolumeBreakdown } from "@/components/gym/VolumeBreakdown";
import { api } from "@/lib/api";
import { translateDiscipline } from "@/lib/labels";
import type { GymSession, Session } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

function isGymSession(session: Session | GymSession): session is GymSession {
  return "workoutExercises" in session;
}

export default function EntrenoDetalle() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | GymSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <main className="dashboard">
      <BottomNav />

      <p>
        <Link className="back-link" href="/entrenos">
          ← Volver a Entrenos
        </Link>
      </p>

      {loading ? (
        <p className="muted">Cargando...</p>
      ) : error ? (
        <p className="error">{error}</p>
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
          </section>

          {isGym ? (
            <>
              <ExerciseRoutine exercises={session.workoutExercises} />
              <ExerciseStatsPlaceholder exercises={session.workoutExercises} />
              <VolumeBreakdown session={session} />
              <CaloriesCard session={session} />
              <MuscleFatigue impacts={session.muscleImpacts} />
            </>
          ) : (
            <>
              <ActivityStats session={session} />
              <MuscleFatigue impacts={session.muscleImpacts ?? []} />
              <CaloriesCard session={session} />

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
    </main>
  );
}
