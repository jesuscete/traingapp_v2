"use client";

import { ExternalLink, Link2Off, RefreshCw, Watch } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { GarminStatus } from "@/lib/types";

const KEY_URL = "https://connect.garmin.com/app/settings/personalApiToken";

function formatWhen(iso: string | null): string {
  if (!iso) return "nunca";
  return new Date(iso).toLocaleString("es-ES", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function GarminCard({ token }: { token: string }) {
  const [status, setStatus] = useState<GarminStatus | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .garminStatus(token)
      .then(setStatus)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Error"));
  }, [token]);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  }

  const connect = () =>
    run(async () => {
      const next = await api.garminConnect(token, apiKey.trim());
      setApiKey("");
      setStatus(next);
      setMessage("Conectado. Importando tus últimos 30 días…");
      const result = await api.garminSync(token);
      setStatus(result.status);
      setMessage(
        `Listo: ${result.imported} actividades nuevas y ${result.healthDays} días de salud.`,
      );
    });

  const sync = (days?: number) =>
    run(async () => {
      const result = await api.garminSync(token, { days });
      setStatus(result.status);
      setMessage(
        `${result.imported} nuevas, ${result.skipped} ya estaban` +
          (result.errors ? `, ${result.errors} con error` : "") +
          (result.healthDays ? ` · ${result.healthDays} días de salud` : ""),
      );
    });

  const disconnect = () =>
    run(async () => {
      if (!window.confirm("¿Desconectar Garmin? Las actividades ya importadas se conservan.")) {
        return;
      }
      await api.garminDisconnect(token);
      setStatus({ ...(status as GarminStatus), connected: false });
      setMessage("Garmin desconectado. Borra también la clave en Garmin Connect si no la usas.");
    });

  return (
    <section className="energy-card garmin-card">
      <h3 className="garmin-title">
        <Watch size={20} strokeWidth={1.75} aria-hidden /> Garmin
      </h3>
      {!status ? (
        <p className="muted">Cargando…</p>
      ) : status.connected ? (
        <>
          <p className="subtitle">
            Sincroniza solo cada 30 min y al abrir la app: actividades (con FC, ritmo y mapa) y
            salud diaria (FC en reposo, sueño y VFC para la fatiga).
          </p>
          <p>
            Última sincronización: <strong>{formatWhen(status.lastSyncAt)}</strong>
          </p>
          {status.status === "error" && status.lastError && (
            <p className="error">
              {status.lastError}. Si la clave ha caducado, crea otra y vuelve a conectar.
            </p>
          )}
          {status.tokenExpiresAt && status.status !== "error" && (
            <p className="muted">Datos de Garmin Connect.</p>
          )}
          <div className="garmin-actions">
            <button type="button" onClick={() => sync()} disabled={busy}>
              <RefreshCw size={16} aria-hidden /> {busy ? "Sincronizando…" : "Sincronizar ahora"}
            </button>
            <button type="button" className="secondary" onClick={() => sync(90)} disabled={busy}>
              Traer últimos 90 días
            </button>
            <button type="button" className="link" onClick={disconnect} disabled={busy}>
              <Link2Off size={16} aria-hidden /> Desconectar
            </button>
          </div>
          {status.status === "error" && (
            <KeyForm apiKey={apiKey} setApiKey={setApiKey} busy={busy} onSubmit={connect} />
          )}
        </>
      ) : (
        <>
          <p className="subtitle">
            Conecta tu cuenta con la clave personal de Garmin (gratuita, solo lectura de tus
            datos). Tus actividades y tu salud diaria llegarán solas.
          </p>
          <ol className="garmin-steps">
            <li>
              Abre{" "}
              <a href={KEY_URL} target="_blank" rel="noreferrer">
                Garmin Connect → Clave de API personal <ExternalLink size={12} aria-hidden />
              </a>{" "}
              (en la web, con tu cuenta).
            </li>
            <li>Pulsa «Create Key», acepta y elige la caducidad (mejor 1 año).</li>
            <li>Copia la clave (solo se muestra una vez) y pégala aquí.</li>
          </ol>
          <KeyForm apiKey={apiKey} setApiKey={setApiKey} busy={busy} onSubmit={connect} />
          <p className="muted">La clave se guarda cifrada y solo la usa este servidor.</p>
        </>
      )}
      {message && <p className="success">{message}</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}

function KeyForm({
  apiKey,
  setApiKey,
  busy,
  onSubmit,
}: {
  apiKey: string;
  setApiKey: (value: string) => void;
  busy: boolean;
  onSubmit: () => void;
}) {
  return (
    <form
      className="garmin-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      <input
        type="password"
        autoComplete="off"
        placeholder="Clave de API personal de Garmin"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        required
        minLength={10}
      />
      <button type="submit" disabled={busy || apiKey.trim().length < 10}>
        {busy ? "Conectando…" : "Conectar"}
      </button>
    </form>
  );
}
