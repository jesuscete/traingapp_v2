"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { hasSession, saveSession } from "@/lib/session";

const REMEMBER_KEY = "traingapp_remember";
const LAST_EMAIL_KEY = "traingapp_last_email";

function readPref(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [remember, setRemember] = useState(true);

  useEffect(() => {
    // Sesión recordada y vigente: directo al inicio.
    if (hasSession()) {
      router.replace("/dashboard");
      return;
    }
    const saved = readPref(REMEMBER_KEY);
    if (saved !== null) setRemember(saved === "1");
    const lastEmail = readPref(LAST_EMAIL_KEY);
    if (lastEmail) setEmail(lastEmail);
  }, [router]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const data = await api.login({ email, password, remember });
      saveSession(data, remember);
      localStorage.setItem(REMEMBER_KEY, remember ? "1" : "0");
      if (remember) localStorage.setItem(LAST_EMAIL_KEY, email);
      else localStorage.removeItem(LAST_EMAIL_KEY);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error de autenticación");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth">
      <div className="card">
        <h1>TraingApp</h1>
        <p className="subtitle">
          Registra tus entrenamientos con el chat de IA
        </p>
        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <label className="remember-me">
              <input
                type="checkbox"
                checked={remember}
                onChange={(e) => setRemember(e.target.checked)}
              />
              Recuérdame (30 días)
            </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "Espera..." : "Entrar"}
          </button>
        </form>
        <Link className="link" href="/registro">
          ¿No tienes cuenta? Crea una
        </Link>
      </div>
    </main>
  );
}
