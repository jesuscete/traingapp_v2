"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { hasSession, saveSession } from "@/lib/session";

const REMEMBER_KEY = "traingapp_remember";
const LAST_EMAIL_KEY = "traingapp_last_email";

export default function Registro() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [remember, setRemember] = useState(true);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (hasSession()) router.replace("/dashboard");
  }, [router]);

  function validate(): Record<string, string> {
    const e: Record<string, string> = {};
    if (!name.trim()) e.name = "Escribe tu nombre";
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) e.email = "Introduce un email válido";
    if (password.length < 8) e.password = "La contraseña debe tener al menos 8 caracteres";
    if (password2 !== password) e.password2 = "Las contraseñas no coinciden";
    return e;
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setLoading(true);
    try {
      const data = await api.register({
        email: email.trim(),
        password,
        name: name.trim(),
        remember,
      });
      saveSession(data, remember);
      localStorage.setItem(REMEMBER_KEY, remember ? "1" : "0");
      if (remember) localStorage.setItem(LAST_EMAIL_KEY, email.trim());
      else localStorage.removeItem(LAST_EMAIL_KEY);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al crear la cuenta");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth">
      <div className="card">
        <h1>Crea tu cuenta</h1>
        <p className="subtitle">Registra tus entrenamientos con el chat de IA</p>
        <form onSubmit={handleSubmit} noValidate>
          <input
            type="text"
            placeholder="Nombre"
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          {errors.name && <p className="error">{errors.name}</p>}
          <input
            type="email"
            placeholder="Email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          {errors.email && <p className="error">{errors.email}</p>}
          <input
            type="password"
            placeholder="Contraseña (mín. 8 caracteres)"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {errors.password && <p className="error">{errors.password}</p>}
          <input
            type="password"
            placeholder="Repetir contraseña"
            autoComplete="new-password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
          />
          {errors.password2 && <p className="error">{errors.password2}</p>}
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
            {loading ? "Espera..." : "Crear cuenta"}
          </button>
        </form>
        <Link className="link" href="/">
          ¿Ya tienes cuenta? Entra
        </Link>
      </div>
    </main>
  );
}
