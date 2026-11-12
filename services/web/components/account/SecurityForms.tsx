"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { useToken } from "@/lib/useToken";

const USER_KEY = "traingapp_user";

export function SecurityForms() {
  const token = useToken();
  const [profile, setProfile] = useState<User | null>(null);

  useEffect(() => {
    if (!token) return;
    api.getProfile(token).then(setProfile).catch(() => setProfile(null));
  }, [token]);

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
    <div className="tab-body">
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
    </div>
  );
}
