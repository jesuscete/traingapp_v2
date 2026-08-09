"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
import { HelpTip } from "@/components/HelpTip";
import { RadarChart } from "@/components/RadarChart";
import {
  translateDiscipline,
  translateInsightMessage,
  translateMuscleGroup,
} from "@/lib/labels";
import type {
  StatsCardio,
  StatsOverview,
  StatsProgress,
  StatsVolume,
  User,
} from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

export default function Dashboard() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [overview, setOverview] = useState<StatsOverview | null>(null);
  const [volume, setVolume] = useState<StatsVolume | null>(null);
  const [volumeWeek, setVolumeWeek] = useState<StatsVolume | null>(null);
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
    const storedUser = localStorage.getItem(USER_KEY);
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch {
        setUser(null);
      }
    }
    loadAll(stored);
  }, [router]);

  const loadAll = useCallback(async (accessToken: string) => {
    setLoading(true);
    try {
      const [o, v, vw, c, p] = await Promise.all([
        api.statsOverview(accessToken),
        api.statsVolume(accessToken),
        api.statsVolume(accessToken, 7),
        api.statsCardio(accessToken),
        api.statsProgress(accessToken),
      ]);
      setOverview(o);
      setVolume(v);
      setVolumeWeek(vw);
      setCardio(c);
      setProgress(p);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar datos");
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleChat(event: React.FormEvent) {    event.preventDefault();
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

  const disciplines = overview?.byDiscipline ?? [];
  const maxGroupVolume = volumeWeek?.byMuscleGroup[0]?.volumeKg ?? 0;
  const radarData = (volumeWeek?.byMuscleGroup ?? [])
    .filter((g) => g.volumeKg > 0)
    .map((g) => ({
      label: translateMuscleGroup(g.muscleGroup),
      value: maxGroupVolume ? g.volumeKg / maxGroupVolume : 0,
    }));

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>
          Hola{user?.name ? `, ${user.name}` : ""} 👋
        </h2>
        <p className="subtitle">Resumen de tu semana</p>
      </section>

      <section className="stats">
        <div className="stat-card">
          <span className="stat-label">
            <HelpTip tip="Suma de kilos levantados en la última semana (series × repeticiones × peso).">
              Volumen semanal
            </HelpTip>
          </span>
          <span className="stat-value">
            {Math.round(volumeWeek?.totalVolumeKg ?? 0)} kg
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">
            <HelpTip tip="Número de entrenamientos registrados en los últimos 30 días.">
              Sesiones (30d)
            </HelpTip>
          </span>
          <span className="stat-value">{overview?.totalSessions ?? "—"}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">
            <HelpTip tip="Media de sesiones registradas por semana.">
              Adherencia
            </HelpTip>
          </span>
          <span className="stat-value">
            {overview ? `${overview.sessionsPerWeek.toFixed(1)}/sem` : "—"}
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">
            <HelpTip tip="Kilos totales levantados en los últimos 90 días.">
              Volumen (90d)
            </HelpTip>
          </span>
          <span className="stat-value">
            {Math.round(volume?.totalVolumeKg ?? 0)} kg
          </span>
        </div>
      </section>

      {loading ? (
        <p className="muted">Cargando...</p>
      ) : (
        <>
          {disciplines.length > 0 && (
            <section className="block">
              <h2>Disciplinas practicadas</h2>
              <div className="chips">
                {disciplines.map((item) => (
                  <span key={item.discipline} className="chip">
                    {translateDiscipline(item.discipline)} · {item.sessions}{" "}
                    {item.sessions === 1 ? "sesión" : "sesiones"}
                  </span>
                ))}
              </div>
            </section>
          )}

          <section className="home-grid">
            {radarData.length >= 3 && (
              <div className="block">
                <h2>Carga por grupo muscular (7d)</h2>
                <RadarChart data={radarData} />
              </div>
            )}

            <div className="block">
              <h2>Registrar entreno</h2>
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
            </div>
          </section>

          {progress && progress.insights.length > 0 && (
            <section className="block insights">
              <h2>Observaciones</h2>
              {progress.insights.map((insight) => (
                <p
                  key={insight.kind}
                  className={`insight insight-${insight.severity}`}
                >
                  {translateInsightMessage(insight.message)}
                </p>
              ))}
            </section>
          )}

          {volume && volume.byMuscleGroup.length > 0 && (
            <section className="block">
              <h2>Volumen por grupo muscular (90d)</h2>
              <div className="bars">
                {volume.byMuscleGroup.map((group) => (
                  <div key={group.muscleGroup} className="bar-row">
                    <span className="bar-label">
                      {translateMuscleGroup(group.muscleGroup)}
                    </span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${
                            maxGroupVolume
                              ? (group.volumeKg / volume.byMuscleGroup[0].volumeKg) *
                                100
                              : 0
                          }%`,
                        }}
                      />
                    </div>
                    <span className="bar-value">
                      {Math.round(group.volumeKg)} kg · {group.sessions}{" "}
                      {group.sessions === 1 ? "ses" : "ses"}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {cardio && cardio.byDiscipline.length > 0 && (
            <section className="block">
              <h2>Cardio</h2>
              <table className="plain">
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
                      <td>{translateDiscipline(item.discipline)}</td>
                      <td>{item.sessions}</td>
                      <td>{item.durationMinutes} min</td>
                      <td>{item.avgDurationMinutes} min</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          )}
        </>
      )}
    </main>
  );
}
