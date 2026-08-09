"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { TopNav } from "@/components/TopNav";
import { DISCIPLINE_LABELS, translateDiscipline } from "@/lib/labels";
import type { Energy, User } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const GOALS: Record<string, string> = {
  loss: "Pérdida de grasa",
  maintenance: "Mantenimiento",
  performance: "Rendimiento",
};

const GOAL_LABELS: Record<string, string> = {
  loss: "Pérdida",
  maintenance: "Mantenimiento",
  performance: "Rendimiento",
};

const SPORT_KEYS = ["gym", "boxing", "running", "cycling", "swimming", "other"];

export default function Perfil() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<User | null>(null);
  const [energy, setEnergy] = useState<Energy | null>(null);
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [sex, setSex] = useState("");
  const [goal, setGoal] = useState("");
  const [sports, setSports] = useState<string[]>([]);
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
    load(stored);
  }, [router]);

  const load = useCallback(async (accessToken: string) => {
    setLoading(true);
    try {
      const p = await api.getProfile(accessToken);
      setProfile(p);
      setWeight(p.weightKg != null ? String(p.weightKg) : "");
      setHeight(p.heightCm != null ? String(p.heightCm) : "");
      setBirthYear(p.birthYear != null ? String(p.birthYear) : "");
      setSex(p.sex ?? "");
      setGoal(p.goal ?? "");
      setSports(p.sports ?? []);
      try {
        const e = await api.statsEnergy(accessToken);
        setEnergy(e);
      } catch {
        setEnergy(null);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar el perfil");
    } finally {
      setLoading(false);
    }
  }, []);

  function toggleSport(key: string) {
    setSports((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key],
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const body: Partial<User> = {
        weightKg: weight !== "" ? Number(weight) : null,
        heightCm: height !== "" ? Number(height) : null,
        birthYear: birthYear !== "" ? Number(birthYear) : null,
        sex: sex !== "" ? sex : null,
        goal: goal !== "" ? goal : null,
        sports: sports.length > 0 ? sports : null,
      };
      const updated = await api.updateProfile(token, body);
      setProfile(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      const e = await api.statsEnergy(token);
      setEnergy(e);
      setMessage("Perfil guardado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar el perfil");
    } finally {
      setSaving(false);
    }
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    router.replace("/");
  }

  return (
    <main className="dashboard">
      <TopNav onLogout={logout} />

      <section className="welcome">
        <h2>Perfil</h2>
        <p className="subtitle">
          {profile?.name ?? "Tu información"}
          {profile?.email ? ` · ${profile.email}` : ""}
        </p>
      </section>

      {loading ? (
        <p className="muted">Cargando...</p>
      ) : (
        <form className="profile-form" onSubmit={handleSubmit}>
          <label>
            Peso (kg)
            <input
              type="number"
              min="20"
              max="400"
              step="0.1"
              placeholder="Ej: 75"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>

          <label>
            Altura (cm)
            <input
              type="number"
              min="80"
              max="250"
              placeholder="Ej: 180"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
            />
          </label>

          <label>
            Año de nacimiento
            <input
              type="number"
              min="1900"
              max="2100"
              placeholder="Ej: 1990"
              value={birthYear}
              onChange={(e) => setBirthYear(e.target.value)}
            />
          </label>

          <label>
            Sexo
            <select value={sex} onChange={(e) => setSex(e.target.value)}>
              <option value="">— Sin definir —</option>
              <option value="male">Masculino</option>
              <option value="female">Femenino</option>
            </select>
          </label>

          <label>
            Objetivo
            <select value={goal} onChange={(e) => setGoal(e.target.value)}>
              <option value="">— Sin definir —</option>
              {Object.entries(GOALS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>

          <fieldset className="sports-field">
            <legend>Disciplinas que practicas</legend>
            <div className="chips">
              {SPORT_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className={`chip chip-toggle${sports.includes(key) ? " on" : ""}`}
                  onClick={() => toggleSport(key)}
                >
                  {DISCIPLINE_LABELS[key] ?? translateDiscipline(key)}
                </button>
              ))}
            </div>
          </fieldset>

          {error && <p className="error">{error}</p>}
          {message && <p className="ok">{message}</p>}

          <button type="submit" disabled={saving}>
            {saving ? "Guardando..." : "Guardar perfil"}
          </button>
        </form>
      )}

      {energy?.tdeeKcal != null && (
        <section className="energy-card">
          <h3>Necesidades calóricas</h3>
          <p className="subtitle">
            Estimación Mifflin-St Jeor (actividad moderada). Para cálculo
            preciso completa peso, altura, año y sexo.
          </p>
          <div className="stats">
            <div className="stat-card">
              <span className="stat-label">Metabolismo basal (BMR)</span>
              <span className="stat-value">{Math.round(energy.bmrKcal!)} kcal</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Gasto total (TDEE)</span>
              <span className="stat-value">{Math.round(energy.tdeeKcal)} kcal</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">
                Objetivo ({GOAL_LABELS[energy.goal ?? ""] ?? "mantener"})
              </span>
              <span className="stat-value">
                {energy.targetKcal != null ? Math.round(energy.targetKcal) : "—"} kcal
              </span>
            </div>
          </div>
        </section>
      )}
    </main>
  );
}
