"use client";

import { Download, LogOut, ShieldCheck, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api } from "@/lib/api";
import { clearSession } from "@/lib/session";

export function AccountCard({ token }: { token: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [password, setPassword] = useState("");

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  const logoutAll = () =>
    run(async () => {
      if (!window.confirm("¿Cerrar la sesión en todos tus dispositivos, también en este?")) return;
      await api.logoutAll(token);
      clearSession();
      router.replace("/");
    });

  const exportData = () =>
    run(async () => {
      const data = await api.exportAccount(token);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `traingapp-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    });

  const deleteAccount = () =>
    run(async () => {
      await api.deleteAccount(token, password);
      clearSession();
      router.replace("/");
    });

  return (
    <section className="energy-card account-card">
      <h3 className="garmin-title">
        <ShieldCheck size={20} strokeWidth={1.75} aria-hidden /> Cuenta y seguridad
      </h3>
      <p className="subtitle">
        La sesión se renueva sola mientras uses la app. Si pierdes el móvil, cierra todas las
        sesiones.
      </p>
      <div className="garmin-actions">
        <button type="button" className="secondary" onClick={logoutAll} disabled={busy}>
          <LogOut size={16} aria-hidden /> Cerrar sesión en todos los dispositivos
        </button>
        <button type="button" className="secondary" onClick={exportData} disabled={busy}>
          <Download size={16} aria-hidden /> Descargar mis datos
        </button>
      </div>

      {!confirmDelete ? (
        <button
          type="button"
          className="link danger-link"
          onClick={() => setConfirmDelete(true)}
          disabled={busy}
        >
          <Trash2 size={16} aria-hidden /> Borrar mi cuenta
        </button>
      ) : (
        <form
          className="garmin-form"
          onSubmit={(e) => {
            e.preventDefault();
            void deleteAccount();
          }}
        >
          <p className="error">
            Se borrarán tu cuenta y todos tus datos (entrenos, comidas, rutinas, objetivos) para
            siempre. Descarga antes tus datos si los quieres conservar.
          </p>
          <input
            type="password"
            autoComplete="current-password"
            placeholder="Tu contraseña para confirmar"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="danger" disabled={busy || !password}>
            Borrar definitivamente
          </button>
          <button type="button" className="link" onClick={() => setConfirmDelete(false)}>
            Cancelar
          </button>
        </form>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
