"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
import { HelpTip } from "@/components/HelpTip";
import { RadarChart } from "@/components/RadarChart";
import { translateMuscleGroup } from "@/lib/labels";
import type { Fatigue, Readiness } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const LEVEL_LABELS: Record<string, string> = {
  ok: "Recuperado",
  warning: "Cargado",
  danger: "Riesgo",
};

export default function Fatiga() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [fatigue, setFatigue] = useState<Fatigue | null>(null);
  const [projectDays, setProjectDays] = useState(0);
  const [sleep, setSleep] = useState("");
  const [doms, setDoms] = useState("");
  const [restDay, setRestDay] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
    load(stored, 0);
  }, [router]);

  const load = useCallback(async (accessToken: string, days: number) => {
    setLoading(true);
    try {
      const data = await api.statsFatigue(accessToken, days);
      setFatigue(data);
      const readiness = data.readiness;
      setSleep(readiness?.sleepHours != null ? String(readiness.sleepHours) : "");
      setDoms(readiness?.doms != null ? String(readiness.doms) : "");
      setRestDay(readiness?.restDay ?? false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar la fatiga");
    } finally {
      setLoading(false);
    }
  }, []);

  function changeProject(days: number) {
    setProjectDays(days);
    if (token) load(token, days);
  }

  async function handleSave(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const body: Partial<Readiness> = {
        date: new Date().toISOString().slice(0, 10),
        sleepHours: sleep !== "" ? Number(sleep) : null,
        doms: doms !== "" ? Number(doms) : null,
        restDay,
      };
      await api.saveReadiness(token, body);
      await load(token, projectDays);
      setMessage("Readiness guardada");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar readiness");
    } finally {
      setSaving(false);
    }
  }

  const radarData = (fatigue?.muscles ?? []).map((m) => ({
    label: translateMuscleGroup(m.muscleGroup),
    value: m.fatigue / 100,
  }));

  return (
    <main className="dashboard">
      <BottomNav />

      <p>
        <Link className="back-link" href="/analisis">
          ← Volver a Análisis
        </Link>
      </p>

      <section className="welcome">
        <h2>Fatiga muscular</h2>
        <p className="subtitle">
          Estimación por grupo muscular (0–100) basada en carga y recuperación.
        </p>
      </section>

      {loading ? (
        <p className="muted">Cargando...</p>
      ) : (
        <>
          <section className="fatigue-toolbar">
            <label>
              Proyección
              <select
                value={projectDays}
                onChange={(e) => changeProject(Number(e.target.value))}
              >
                <option value={0}>Hoy</option>
                <option value={1}>Mañana</option>
                <option value={2}>+2 días</option>
                <option value={3}>+3 días</option>
                <option value={5}>+5 días</option>
                <option value={7}>+7 días</option>
              </select>
            </label>
            <span className="muted">
              {fatigue?.projected
                ? `Predicción para ${fatigue.projected}`
                : ""}
            </span>
          </section>

          <section className="home-grid">
            <div className="block">
              <h2>
                <HelpTip tip="Fatiga estimada por grupo (0-100). Verde ≤ 40, ámbar 41-70, rojo > 70. Modelo impulso-respuesta con doble exponencial (ver docs/architecture/fatigue-spec.md).">
                  Radar de fatiga
                </HelpTip>
              </h2>
              <RadarChart data={radarData} size={420} showLabels />
              <div className="fatigue-scale">
                <span className="scale-ok">≤ 40</span>
                <span className="scale-warn">41–70</span>
                <span className="scale-danger">&gt; 70</span>
              </div>
            </div>

            <div className="block">
              <h2>Readiness</h2>
              <form className="profile-form" onSubmit={handleSave}>
                <label>
                  Horas de sueño
                  <input
                    type="number"
                    min="0"
                    max="24"
                    step="0.5"
                    placeholder="Ej: 7.5"
                    value={sleep}
                    onChange={(e) => setSleep(e.target.value)}
                  />
                </label>
                <label>
                  Dolor muscular (DOMS 1–10)
                  <input
                    type="number"
                    min="1"
                    max="10"
                    placeholder="Ej: 3"
                    value={doms}
                    onChange={(e) => setDoms(e.target.value)}
                  />
                </label>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={restDay}
                    onChange={(e) => setRestDay(e.target.checked)}
                  />
                  Día de descanso
                </label>
                <button type="submit" disabled={saving}>
                  {saving ? "Guardando..." : "Guardar readiness"}
                </button>
              </form>
              {message && <p className="ok">{message}</p>}
              {error && <p className="error">{error}</p>}
            </div>
          </section>

          {fatigue && fatigue.risks.length > 0 && (
            <section className="block insights">
              <h2>Señales de sobrecarga</h2>
              {fatigue.risks.map((risk) => (
                <div key={risk.muscleGroup} className="risk-item">
                  <strong>
                    {translateMuscleGroup(risk.muscleGroup)} ·{" "}
                    {LEVEL_LABELS[risk.level] ?? risk.level}
                  </strong>
                  {risk.reasons.length > 0 && (
                    <ul>
                      {risk.reasons.map((reason) => (
                        <li key={reason}>{reason}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </section>
          )}

          {fatigue && (
            <section className="block">
              <h2>Fatiga por grupo</h2>
              <div className="bars">
                {fatigue.muscles
                  .slice()
                  .sort((a, b) => b.fatigue - a.fatigue)
                  .map((m) => (
                    <div key={m.muscleGroup} className="bar-row">
                      <span className="bar-label">
                        {translateMuscleGroup(m.muscleGroup)}
                      </span>
                      <div className="bar-track">
                        <div
                          className={`bar-fill fatigue-${m.level}`}
                          style={{ width: `${Math.max(0, Math.min(100, m.fatigue))}%` }}
                        />
                      </div>
                      <span className="bar-value">
                        {Math.round(m.fatigue)} · ACWR {m.acwr.toFixed(1)}
                      </span>
                    </div>
                  ))}
              </div>
            </section>
          )}
        </>
      )}
    </main>
  );
}
