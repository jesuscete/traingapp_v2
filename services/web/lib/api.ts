import type {
  ChatEnqueue,
  Session,
  StatsCardio,
  StatsOverview,
  StatsProgress,
  StatsVolume,
  TokenResponse,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      body && typeof body === "object" && "detail" in body
        ? String(body.detail)
        : `Error ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export type Credentials = { email: string; password: string };
export type Registration = Credentials & { name: string };

export const api = {
  login: (body: Credentials) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  register: (body: Registration) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listSessions: (token: string) =>
    request<Session[]>("/sessions", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  sendChat: (token: string, text: string) =>
    request<ChatEnqueue>("/chat/message", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text }),
    }),
  statsOverview: (token: string) =>
    request<StatsOverview>("/stats/overview", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsVolume: (token: string) =>
    request<StatsVolume>("/stats/volume", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsCardio: (token: string) =>
    request<StatsCardio>("/stats/cardio", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsProgress: (token: string) =>
    request<StatsProgress>("/stats/progress", {
      headers: { Authorization: `Bearer ${token}` },
    }),
};
