"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { TopNav } from "@/components/TopNav";
import { translateDiscipline } from "@/lib/labels";
import type { Session } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";

export default function Entrenos() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    loadAll(stored);
  }, [router]);

  const loadAll = useCallback(async (accessToken: string) => {
    setLoading(true);
    try {
      const s = await api.listSessions(accessToken);
      setSessions(s);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
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

      <section className="welcome">
        <h2>Entrenos</h2>
        <p className="subtitle">
          {sessions.length > 0
            ? `Tienes ${sessions.length} ${sessions.length === 1 ? "entrenamiento" : "entrenamientos"} registrados`
            : "Aún no has registrado entrenamientos"}
        </p>
      </section>

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="muted">Cargando...</p>
      ) : sessions.length === 0 ? (
        <p className="muted">
          Registra tu primer entreno desde el chat de Inicio.
        </p>
      ) : (
        <table className="plain sessions-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Disciplina</th>
              <th>Entrenamiento</th>
              <th>Duración</th>
              <th>Volumen</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>{new Date(s.performedAt).toLocaleDateString()}</td>
                <td>
                  <span className="chip">{translateDiscipline(s.discipline)}</span>
                </td>
                <td>
                  <Link className="session-link" href={`/entrenos/${s.id}`}>
                    {s.rawText}
                  </Link>
                </td>
                <td>
                  {s.durationMinutes != null ? `${s.durationMinutes} min` : "—"}
                </td>
                <td>{Math.round(s.volumeKg)} kg</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  );
}
