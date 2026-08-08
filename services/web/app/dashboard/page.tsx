"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type {
  Session,
  StatsCardio,
  StatsOverview,
  StatsProgress,
  StatsVolume,
} from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export default function Dashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [volume, setVolume] = useState<StatsVolume | null>(null);
  const [cardio, setCardio] = useState<StatsCardio | null>(null);
  const [progress, setProgress] = useState<StatsProgress | null>(null);
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
    loadAll(stored);
  }, [router]);

  const loadAll = useCallback(async (accessToken: string) => {
    setLoading(true);
    try {
      const [s, o, v, c, p] = await Promise.all([
        api.listSessions(accessToken),
        api.statsOverview(accessToken),
        api.statsVolume(accessToken),
        api.statsCardio(accessToken),
        api.statsProgress(accessToken),
      ]);
      setSessions(s);
      setOverview(o);
      setVolume(v);
      setCardio(c);
      setProgress(p);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
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
      setTimeout(() => loadAll(token), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al enviar el chat");
    }
  }

  const now = Date.now();
  const weeklyVolume = sessions
    .filter((s) => now - new Date(s.performedAt).getTime() < WEEK_MS)
    .reduce((sum, s) => sum + (s.volumeKg ?? 0), 0);

  const maxGroupVolume = volume?.byMuscleGroup[0]?.volumeKg ?? 0;

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
          <span className="stat-label">Sesiones (30d)</span>
          <span className="stat-value">{overview?.totalSessions ?? "—"}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Adherencia</span>
          <span className="stat-value">
            {overview ? `${overview.sessionsPerWeek.toFixed(1)}/sem` : "—"}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Volumen (90d)</span>
          <span className="stat-value">
            {Math.round(volume?.totalVolumeKg ?? 0)} kg
          </span>
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

      {progress && progress.insights.length > 0 && (
        <section className="insights">
          <h2>Observaciones</h2>
          {progress.insights.map((insight) => (
            <p
              key={insight.kind}
              className={`insight insight-${insight.severity}`}
            >
              {insight.message}
            </p>
          ))}
        </section>
      )}

      {volume && volume.byMuscleGroup.length > 0 && (
        <section className="block">
          <h2>Volumen por grupo muscular</h2>
          <div className="bars">
            {volume.byMuscleGroup.map((group) => (
              <div key={group.muscleGroup} className="bar-row">
                <span className="bar-label">{group.muscleGroup}</span>
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${
                        maxGroupVolume ? (group.volumeKg / maxGroupVolume) * 100 : 0
                      }%`,
                    }}
                  />
                </div>
                <span className="bar-value">
                  {Math.round(group.volumeKg)} kg · {group.sessions} ses
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {volume && volume.exerciseProgress.length > 0 && (
        <section className="block">
          <h2>Progresión 1RM estimada</h2>
          <table>
            <thead>
              <tr>
                <th>Ejercicio</th>
                <th>1RM</th>
                <th>Delta</th>
              </tr>
            </thead>
            <tbody>
              {volume.exerciseProgress.slice(0, 8).map((item) => (
                <tr key={item.exercise}>
                  <td>{item.exercise}</td>
                  <td>{item.best1Rm != null ? `${item.best1Rm.toFixed(0)} kg` : "—"}</td>
                  <td>
                    {item.deltaPct != null ? (
                      <span className={item.deltaPct >= 0 ? "ok" : "error"}>
                        {item.deltaPct >= 0 ? "▲" : "▼"} {item.deltaPct.toFixed(1)}%
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {cardio && cardio.byDiscipline.length > 0 && (
        <section className="block">
          <h2>Cardio</h2>
          <table>
            <thead>
              <tr>
                <th>Disciplina</th>
                <th>Sesiones</th>
                <th>Duración total</th>
                <th>Media</th>
              </tr>
            </thead>
            <tbody>
              {cardio.byDiscipline.map((item) => (
                <tr key={item.discipline}>
                  <td>{item.discipline}</td>
                  <td>{item.sessions}</td>
                  <td>{item.durationMinutes} min</td>
                  <td>{item.avgDurationMinutes} min</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="block sessions">
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
