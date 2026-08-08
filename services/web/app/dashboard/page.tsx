"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { Session } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export default function Dashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [chatText, setChatText] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    loadSessions(stored);
  }, [router]);

  const loadSessions = useCallback(async (accessToken: string) => {
    setLoading(true);
    try {
      const data = await api.listSessions(accessToken);
      setSessions(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar sesiones");
    } finally {
      setLoading(false);
    }
  }, []);

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    router.replace("/");
  }

  async function handleChat(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setMessage(null);
    setError(null);
    try {
      await api.sendChat(token, chatText);
      setChatText("");
      setMessage("Entrenamiento enviado a la IA. Procesando...");
      setTimeout(() => loadSessions(token), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar el chat");
    }
  }

  const now = Date.now();
  const weeklyVolume = sessions
    .filter((s) => now - new Date(s.performedAt).getTime() < WEEK_MS)
    .reduce((sum, s) => sum + (s.volumeKg ?? 0), 0);

  return (
    <main className="dashboard">
      <header className="topbar">
        <h1>TraingApp</h1>
        <button type="button" className="link" onClick={logout}>
          Salir
        </button>
      </header>

      <section className="stats">
        <div className="stat-card">
          <span className="stat-label">Volumen semanal</span>
          <span className="stat-value">{Math.round(weeklyVolume)} kg</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Sesiones</span>
          <span className="stat-value">{sessions.length}</span>
        </div>
      </section>

      <form className="chat" onSubmit={handleChat}>
        <input
          type="text"
          placeholder='Ej: "5x5 press banca 80kg" o "clase de boxeo de 1h30m"'
          value={chatText}
          onChange={(e) => setChatText(e.target.value)}
          required
        />
        <button type="submit">Registrar</button>
      </form>
      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="sessions">
        <h2>Historial</h2>
        {loading ? (
          <p>Cargando...</p>
        ) : sessions.length === 0 ? (
          <p>No hay entrenamientos registrados todavía.</p>
        ) : (
          <table>
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
                  <td>{s.discipline}</td>
                  <td>{s.rawText}</td>
                  <td>
                    {s.durationMinutes != null ? `${s.durationMinutes} min` : "—"}
                  </td>
                  <td>{Math.round(s.volumeKg)} kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}
