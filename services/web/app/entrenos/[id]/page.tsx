"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { HelpTip } from "@/components/HelpTip";
import { TopNav } from "@/components/TopNav";
import { translateDiscipline } from "@/lib/labels";
import type { Session } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

export default function EntrenoDetalle() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const [token, setToken] = useState<string | null>(null);
  const [session, setSession] = useState<Session | null>(null);
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

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem("traingapp_user");
    router.replace("/");
  }

  return (
    <main className="dashboard">
      <TopNav onLogout={logout} />

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

          <section className="stats">
            <div className="stat-card">
              <span className="stat-label">Volumen</span>
              <span className="stat-value">{Math.round(session.volumeKg)} kg</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Ejercicios</span>
              <span className="stat-value">{session.exercises.length}</span>
            </div>
            {session.estimatedKcal != null && (
              <div className="stat-card">
                <span className="stat-label">
                  <HelpTip tip="Estimación por MET (peso × actividad × duración). Valor aproximado.">
                    Calorías
                  </HelpTip>
                </span>
                <span className="stat-value">
                  {Math.round(session.estimatedKcal)} kcal
                </span>
              </div>
            )}
          </section>

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
        </>
      ) : null}
    </main>
  );
}
