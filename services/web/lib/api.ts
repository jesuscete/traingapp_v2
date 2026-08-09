import type {
  ChatEnqueue,
  ChatMessageOut,
  Energy,
  ExerciseDraft,
  Fatigue,
  Readiness,
  Session,
  StatsCardio,
  StatsOverview,
  StatsProgress,
  StatsVolume,
  TokenResponse,
  User,
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
  getProfile: (token: string) =>
    request<User>("/profile", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  updateProfile: (token: string, body: Partial<User>) =>
    request<User>("/profile", {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  listSessions: (token: string) =>
    request<Session[]>("/sessions", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getSession: (token: string, id: string) =>
    request<Session>(`/sessions/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  sendChat: (token: string, text: string) =>
    request<ChatEnqueue>("/chat/message", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text }),
    }),
  sendDraft: (token: string, text: string) =>
    request<ChatMessageOut>("/chat/draft", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text }),
    }),
  confirmDraft: (
    token: string,
    body: {
      requestId: string;
      suggestedRpe?: number | null;
      perceivedFatigue?: number | null;
      durationMinutes?: number | null;
      distanceMeters?: number | null;
      workoutType?: string | null;
      exercises?: ExerciseDraft[] | null;
    },
  ) =>
    request<Session>("/chat/confirm", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  cancelDraft: (token: string, requestId: string) =>
    request<{ status: string }>("/chat/cancel", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ requestId }),
    }),
  statsOverview: (token: string) =>
    request<StatsOverview>("/stats/overview", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsVolume: (token: string, days = 90) =>
    request<StatsVolume>(`/stats/volume?days=${days}`, {
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
  statsEnergy: (token: string) =>
    request<Energy>("/stats/energy", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsFatigue: (token: string, projectDays = 0) =>
    request<Fatigue>(`/stats/fatigue?projectDays=${projectDays}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getReadiness: (token: string) =>
    request<Readiness | null>("/stats/readiness", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  saveReadiness: (token: string, body: Partial<Readiness>) =>
    request<Readiness>("/stats/readiness", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
};
