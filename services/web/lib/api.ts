import type {
  CatalogExercise,
  ChatEnqueue,
  ChatMessageOut,
  Discipline,
  Energy,
  ExerciseDraft,
  Fatigue,
  FatigueSeries,
  GymSession,
  HistorySummary,
  LiveSession,
  Load,
  Readiness,
  Routine,
  RoutineDayInput,
  RoutineInput,
  RoutineReview,
  RoutineReviewInput,
  Session,
  SessionPage,
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
    let message = `Error ${response.status}`;
    if (body && typeof body === "object" && "detail" in body) {
      const detail = body.detail;
      message = Array.isArray(detail)
        ? detail.map((item: { msg?: string }) => item.msg ?? String(item)).join("; ")
        : String(detail);
    }
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
  listSessions: (
    token: string,
    params: {
      page?: number;
      pageSize?: number;
      q?: string;
      discipline?: string[];
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.page != null) query.set("page", String(params.page));
    if (params.pageSize != null) query.set("pageSize", String(params.pageSize));
    if (params.q) query.set("q", params.q);
    for (const d of params.discipline ?? []) query.append("discipline", d);
    const qs = query.toString();
    return request<SessionPage>(`/sessions${qs ? `?${qs}` : ""}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },
  getSessionsSummary: (token: string, days: number) =>
    request<HistorySummary>(`/sessions/summary?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getSession: (token: string, id: string) =>
    request<Session | GymSession>(`/sessions/${id}`, {
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
  statsFatigueSeries: (token: string, days = 30) =>
    request<FatigueSeries>(`/stats/fatigue/series?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  statsLoad: (token: string, days = 30) =>
    request<Load>(`/stats/load?days=${days}`, {
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
  listRoutines: (token: string) =>
    request<Routine[]>("/routines", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getActiveRoutine: (token: string) =>
    request<Routine | null>("/routines/active", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  createRoutine: (token: string, body: RoutineInput) =>
    request<Routine>("/routines", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  updateRoutine: (
    token: string,
    routineId: string,
    body: { name?: string | null; isActive?: boolean | null },
  ) =>
    request<Routine>(`/routines/${routineId}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteRoutine: (token: string, routineId: string) =>
    request<void>(`/routines/${routineId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  upsertRoutineDay: (
    token: string,
    routineId: string,
    dayOfWeek: number,
    body: RoutineDayInput,
  ) =>
    request<Routine>(`/routines/${routineId}/days/${dayOfWeek}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteRoutineDay: (token: string, routineId: string, dayOfWeek: number) =>
    request<Routine>(`/routines/${routineId}/days/${dayOfWeek}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  reviewRoutine: (token: string, body: RoutineReviewInput) =>
    request<RoutineReview>("/routines/review", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  listCatalogExercises: (token: string) =>
    request<CatalogExercise[]>("/catalog/exercises", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  listDisciplines: (token: string) =>
    request<Discipline[]>("/catalog/disciplines", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getLive: (token: string) =>
    request<LiveSession | null>("/live", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  startLive: (token: string, routineDayId?: string | null) =>
    request<LiveSession>("/live/start", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ routineDayId: routineDayId ?? null }),
    }),
  patchLiveSet: (
    token: string,
    body: {
      exerciseIndex: number;
      setNumber: number;
      weight?: number | null;
      reps?: number | null;
    },
  ) =>
    request<LiveSession>("/live/set", {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  addLiveExercise: (
    token: string,
    body: {
      name: string;
      exerciseId?: string | null;
      sets: { setNumber: number; weight?: number | null; reps?: number | null }[];
    },
  ) =>
    request<LiveSession>("/live/exercises", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  addLiveSet: (
    token: string,
    exerciseIndex: number,
    body: { setNumber: number; weight?: number | null; reps?: number | null },
  ) =>
    request<LiveSession>(`/live/exercises/${exerciseIndex}/sets`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  finishLive: (
    token: string,
    body: {
      durationMinutes?: number | null;
      intensity?: number | null;
      fatigue?: number | null;
      note?: string | null;
      performedAt?: string | null;
      keepSetsWithoutWeight?: boolean;
    },
  ) =>
    request<GymSession | Session>("/live/finish", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  cancelLive: (token: string) =>
    request<{ status: string }>("/live", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
};
