"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export const TOKEN_KEY = "traingapp_token";

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
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
  }, [router]);
  return token;
}
