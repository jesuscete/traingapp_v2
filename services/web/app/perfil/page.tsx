"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronRight, Target } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
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

export default function Perfil() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<User | null>(null);
  const [energy, setEnergy] = useState<Energy | null>(null);

  const [name, setName] = useState("");
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [birthYear, setBirthYear] = useState("");
  const [sex, setSex] = useState("");
  const [goal, setGoal] = useState("");
  const [maxHr, setMaxHr] = useState("");
  const [restingHr, setRestingHr] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState("");
  const [savingEmail, setSavingEmail] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailMessage, setEmailMessage] = useState<string | null>(null);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordMessage, setPasswordMessage] = useState<string | null>(null);

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
      setBirthYear(p.birthYear != null ? String(p.birthYear) : "");
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
        birthYear: birthYear !== "" ? Number(birthYear) : null,
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

  async function handleEmailSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setSavingEmail(true);
    setEmailMessage(null);
    setEmailError(null);
    try {
      const updated = await api.updateEmail(token, newEmail);
      setProfile(updated);
      localStorage.setItem(USER_KEY, JSON.stringify(updated));
      setNewEmail("");
      setEmailMessage("Email actualizado");
    } catch (err) {
      setEmailError(
        err instanceof Error ? err.message : "Error al cambiar el email",
      );
    } finally {
      setSavingEmail(false);
    }
  }

  async function handlePasswordSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!token) return;
    setPasswordMessage(null);
    setPasswordError(null);
    if (newPassword !== confirmPassword) {
      setPasswordError("Las contraseñas no coinciden");
      return;
    }
    setSavingPassword(true);
    try {
      await api.updatePassword(token, {
        currentPassword,
        newPassword,
      });
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPasswordMessage("Contraseña actualizada");
    } catch (err) {
      setPasswordError(
        err instanceof Error ? err.message : "Error al cambiar la contraseña",
      );
    } finally {
      setSavingPassword(false);
    }
  }

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>Perfil</h2>
        <p className="subtitle">
          {profile?.name ?? "Tu información"}
          {profile?.email ? ` · ${profile.email}` : ""}
        </p>
      </section>

      <div className="hub-grid hub-list">
        <Link className="hub-tile" href="/objetivos">
          <span className="hub-icon">
            <Target size={22} strokeWidth={1.75} aria-hidden="true" />
          </span>
          <span className="hub-text">
            <span className="hub-label">Objetivos y deporte</span>
            <span className="hub-sub">Deporte principal y metas</span>
          </span>
          <ChevronRight className="hub-chev" size={18} strokeWidth={1.75} aria-hidden="true" />
        </Link>
      </div>

      {loading ? (
        <p className="muted">Cargando...</p>
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

      <section className="energy-card">
        <h3>Cambiar email</h3>
        <p className="subtitle">
          Email actual: {profile?.email}. Si ya está registrado, no podrás
          usarlo.
        </p>
        <form className="profile-form" onSubmit={handleEmailSubmit}>
          <input
            type="email"
            placeholder="Nuevo email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            required
          />
          {emailError && <p className="error">{emailError}</p>}
          {emailMessage && <p className="ok">{emailMessage}</p>}
          <button type="submit" disabled={savingEmail}>
            {savingEmail ? "Actualizando..." : "Actualizar email"}
          </button>
        </form>
      </section>

      <section className="energy-card">
        <h3>Cambiar contraseña</h3>
        <form className="profile-form" onSubmit={handlePasswordSubmit}>
          <input
            type="password"
            placeholder="Contraseña actual"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Nueva contraseña"
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Confirmar nueva contraseña"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          {passwordError && <p className="error">{passwordError}</p>}
          {passwordMessage && <p className="ok">{passwordMessage}</p>}
          <button type="submit" disabled={savingPassword}>
            {savingPassword ? "Actualizando..." : "Actualizar contraseña"}
          </button>
        </form>
      </section>
    </main>
  );
}
