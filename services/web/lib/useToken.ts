"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export const TOKEN_KEY = "traingapp_token";

/** true si el JWT aún no ha caducado (se lee `exp` sin verificar la firma). */
export function tokenIsValid(token: string | null): boolean {
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))) as {
      exp?: number;
    };
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/** Devuelve el token (null mientras carga) y redirige al login si no hay. */
export function useToken(): string | null {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  useEffect(() => {
    const stored = readToken();
    if (!tokenIsValid(stored)) {
      router.replace("/");
      return;
    }
    setToken(stored as string);
  }, [router]);
  return token;
}
