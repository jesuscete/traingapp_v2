"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
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

export function ProfileForm() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<User | null>(null);
  const [energy, setEnergy] = useState<Energy | null>(null);

  const [name, setName] = useState("");
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [sex, setSex] = useState("");
  const [goal, setGoal] = useState("");
  const [maxHr, setMaxHr] = useState("");
  const [restingHr, setRestingHr] = useState("");
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
      setName(p.name ?? "");
      setWeight(p.weightKg != null ? String(p.weightKg) : "");
      setHeight(p.heightCm != null ? String(p.heightCm) : "");
      setBirthDate(p.birthDate ?? "");
      setSex(p.sex ?? "");
      setGoal(p.goal ?? "");
      setMaxHr(p.maxHr != null ? String(p.maxHr) : "");
      setRestingHr(p.restingHr != null ? String(p.restingHr) : "");
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

  async function handleProfileSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const body: Partial<User> = {
        ...(name !== "" ? { name } : {}),
        weightKg: weight !== "" ? Number(weight) : null,
        heightCm: height !== "" ? Number(height) : null,
        ...(birthDate !== "" ? { birthDate } : {}),
        sex: sex !== "" ? sex : null,
        goal: goal !== "" ? goal : null,
        maxHr: maxHr !== "" ? Number(maxHr) : null,
        restingHr: restingHr !== "" ? Number(restingHr) : null,
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

  return (
    <div className="tab-body">

      <p className="muted">
        {profile?.name ?? "Tu información"}
        {profile?.email ? ` · ${profile.email}` : ""}
      </p>

      {loading ? (
        <div className="stack"><Skeleton height={48} /><Skeleton height={48} /><Skeleton height={48} /></div>
      ) : (
        <form className="profile-form" onSubmit={handleProfileSubmit}>
          <label>
            Nombre
            <input
              type="text"
              maxLength={120}
              placeholder="Tu nombre"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>

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
            Fecha de nacimiento
            <input
              type="date"
              value={birthDate}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => setBirthDate(e.target.value)}
            />
            {!birthDate && profile?.birthYear != null && (
              <small className="muted">Año: {profile.birthYear}</small>
            )}
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

          <label>
            FC máxima (lpm)
            <input
              type="number"
              min="120"
              max="230"
              placeholder="Ej: 190"
              value={maxHr}
              onChange={(e) => setMaxHr(e.target.value)}
            />
          </label>

          <label>
            FC en reposo (lpm)
            <input
              type="number"
              min="30"
              max="110"
              placeholder="Ej: 55"
              value={restingHr}
              onChange={(e) => setRestingHr(e.target.value)}
            />
          </label>
          <p className="muted">
            Las zonas de FC se calculan por reserva de FC (Karvonen). Si no sabes tu FC máxima se
            estima con 208 − 0,7·edad.
          </p>

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
    </div>
  );
}
