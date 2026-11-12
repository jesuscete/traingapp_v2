/**
 * Sesión: token de acceso corto (15 min) + refresh token rotatorio.
 * - Con «Recuérdame», el refresh vive en localStorage (30 días); sin él, en sessionStorage
 *   (se pierde al cerrar el navegador).
 * - `refreshAccess` renueva el token de acceso una sola vez aunque lo pidan varias
 *   peticiones a la vez.
 */

export const TOKEN_KEY = "traingapp_token";
export const USER_KEY = "traingapp_user";
export const REFRESH_KEY = "traingapp_refresh";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type SessionTokens = {
  access_token: string;
  refresh_token: string;
  user?: unknown;
};

function safe<T>(fn: () => T, fallback: T): T {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

/** true si el JWT aún no ha caducado (se lee `exp` sin verificar la firma). */
export function tokenIsValid(token: string | null, marginSeconds = 0): boolean {
  if (!token) return false;
  try {
    const payload = JSON.parse(
      atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
    ) as { exp?: number };
    return typeof payload.exp === "number" && payload.exp * 1000 > Date.now() + marginSeconds * 1000;
  } catch {
    return false;
  }
}

export function readAccess(): string | null {
  return safe(() => localStorage.getItem(TOKEN_KEY), null);
}

export function readRefresh(): string | null {
  return safe(
    () => localStorage.getItem(REFRESH_KEY) ?? sessionStorage.getItem(REFRESH_KEY),
    null,
  );
}

/** Hay sesión si el token de acceso vale o se puede renovar. */
export function hasSession(): boolean {
  return tokenIsValid(readAccess()) || readRefresh() !== null;
}

export function saveSession(tokens: SessionTokens, remember: boolean): void {
  safe(() => {
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    if (tokens.user !== undefined) localStorage.setItem(USER_KEY, JSON.stringify(tokens.user));
    localStorage.removeItem(REFRESH_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    (remember ? localStorage : sessionStorage).setItem(REFRESH_KEY, tokens.refresh_token);
  }, undefined);
}

function updateTokens(tokens: SessionTokens): void {
  safe(() => {
    localStorage.setItem(TOKEN_KEY, tokens.access_token);
    const store = localStorage.getItem(REFRESH_KEY) !== null ? localStorage : sessionStorage;
    store.setItem(REFRESH_KEY, tokens.refresh_token);
  }, undefined);
}

export function clearSession(): void {
  safe(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REFRESH_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  }, undefined);
}

let inflight: Promise<string | null> | null = null;

/** Renueva el token de acceso con el refresh. Devuelve el nuevo o null si la sesión acabó. */
export function refreshAccess(): Promise<string | null> {
  if (inflight) return inflight;
  const refresh = readRefresh();
  if (!refresh) return Promise.resolve(null);
  inflight = (async () => {
    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refreshToken: refresh }),
      });
      if (!response.ok) {
        if (response.status === 401) clearSession();
        return null;
      }
      const tokens = (await response.json()) as SessionTokens;
      updateTokens(tokens);
      return tokens.access_token;
    } catch {
      return null; // sin red: se reintentará en la siguiente petición
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}

/** Token de acceso vigente (renovándolo si caduca en menos de 30 s). */
export async function currentAccess(): Promise<string | null> {
  const access = readAccess();
  if (tokenIsValid(access, 30)) return access;
  return (await refreshAccess()) ?? (tokenIsValid(access) ? access : null);
}

/** Cierra esta sesión en el servidor (si se puede) y borra los datos locales. */
export async function logout(): Promise<void> {
  const refresh = readRefresh();
  clearSession();
  if (!refresh) return;
  await fetch(`${API_URL}/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refreshToken: refresh }),
  }).catch(() => undefined);
}
