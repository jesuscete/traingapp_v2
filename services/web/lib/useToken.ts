"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { hasSession, readAccess } from "@/lib/session";

export { TOKEN_KEY, tokenIsValid } from "@/lib/session";

export function readToken(): string | null {
  return readAccess();
}

/**
 * Devuelve el token (null mientras carga) y redirige al login si no hay sesión.
 * Aunque el token de acceso haya caducado, si hay refresh la API lo renueva sola.
 */
export function useToken(): string | null {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    if (!hasSession()) {
      router.replace("/");
      return;
    }
    setToken(readAccess() ?? "");
  }, [router]);
  return token;
}
