import type {
  AgentReply,
  Food,
  FoodInput,
  MealEntry,
  MealEntryInput,
  MealName,
  MealTemplate,
  NutritionDay,
  NutritionGoal,
  NutritionWeek,
  ParseMealResult,
  ProposedItem,
  WeightSeries,
  CatalogExercise,
  ExerciseAlternative,
  SportAnalysis,
  CustomExerciseInput,
  ChatEnqueue,
  ChatMessageOut,
  Discipline,
  Energy,
  ExerciseDraft,
  ExerciseHistory,
  FatigueExplain,
  Fatigue,
  FatigueSeries,
  GymSession,
  GymSessionIn,
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
  SessionIn,
  SessionPage,
  SessionUpdate,
  StatsCardio,
  StatsOverview,
  StatsProgress,
  StatsVolume,
  TokenResponse,
  User,
} from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  readonly status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

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
    throw new ApiError(message, response.status);
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
  updateEmail: (token: string, email: string) =>
    request<User>("/profile/email", {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ email }),
    }),
  updatePassword: (
    token: string,
    body: { currentPassword: string; newPassword: string },
  ) =>
    request<User>("/profile/password", {
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
  createSession: (token: string, body: SessionIn) =>
    request<Session>("/sessions", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  updateSession: (token: string, id: string, body: SessionUpdate) =>
    request<Session | GymSession>(`/sessions/${id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  getFatigueExplain: (token: string, group: string, days = 28) =>
    request<FatigueExplain>(
      `/stats/fatigue/explain?group=${encodeURIComponent(group)}&days=${days}`,
      { headers: { Authorization: `Bearer ${token}` } },
    ),
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
  confirmPlan: (token: string, planRequestId: string) =>
    request<ChatMessageOut>("/chat/plan/confirm", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ planRequestId }),
    }),
  cancelPlan: (token: string, planRequestId: string) =>
    request<ChatMessageOut>("/chat/plan/cancel", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ planRequestId }),
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
  duplicateRoutine: (token: string, routineId: string) =>
    request<Routine>(`/routines/${routineId}/duplicate`, {
      method: "POST",
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
  createCustomExercise: (token: string, body: CustomExerciseInput) =>
    request<CatalogExercise>("/catalog/exercises", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteCustomExercise: (token: string, exerciseId: string) =>
    request<void>(`/catalog/exercises/${exerciseId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  setExerciseFavorite: (token: string, exerciseId: string, favorite: boolean) =>
    request<void>(`/catalog/exercises/${exerciseId}/favorite`, {
      method: favorite ? "PUT" : "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  getExerciseHistory: (token: string, exerciseId: string, limit = 20) =>
    request<ExerciseHistory>(
      `/catalog/exercises/${exerciseId}/history?limit=${limit}`,
      { headers: { Authorization: `Bearer ${token}` } },
    ),
  createGymSession: (token: string, body: GymSessionIn) =>
    request<GymSession>("/sessions/gym", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
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
  getSportAnalysis: (
    token: string,
    params: {
      sport?: string;
      weeks?: number;
      basis?: "auto" | "historial" | "rutina";
      narrative?: boolean;
    },
  ) => {
    // Sin sport, el backend usa el deporte principal del perfil.
    const query = new URLSearchParams();
    if (params.sport) query.set("sport", params.sport);
    query.set("weeks", String(params.weeks ?? 4));
    query.set("basis", params.basis ?? "auto");
    query.set("narrative", String(params.narrative ?? false));
    return request<SportAnalysis>(`/analysis/sport?${query.toString()}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  },
  getExerciseAlternatives: (token: string, exerciseId: string, limit = 8) =>
    request<ExerciseAlternative[]>(
      `/catalog/exercises/${exerciseId}/alternatives?limit=${limit}`,
      { headers: { Authorization: `Bearer ${token}` } },
    ),
  swapRoutineExercise: (
    token: string,
    routineId: string,
    routineExerciseId: string,
    exerciseId: string,
  ) =>
    request<Routine>(`/routines/${routineId}/exercises/${routineExerciseId}/swap`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ exerciseId }),
    }),
  addRoutineDayExercise: (
    token: string,
    routineId: string,
    dayOfWeek: number,
    body: {
      exerciseId: string;
      sets?: number;
      targetRepsMin?: number;
      targetRepsMax?: number;
    },
  ) =>
    request<Routine>(`/routines/${routineId}/days/${dayOfWeek}/exercises`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  sendAgentMessage: (token: string, text: string) =>
    request<AgentReply>("/agent/message", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text }),
    }),
  confirmAgentAction: (token: string, actionId: string) =>
    request<{ message: string }>(`/agent/actions/${actionId}/confirm`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }),
  discardAgentAction: (token: string, actionId: string) =>
    request<void>(`/agent/actions/${actionId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  resetAgentConversation: (token: string) =>
    request<void>("/agent/conversation", {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),

  /* ===== M5 nutrición ===== */
  searchFoods: (token: string, q: string) =>
    request<Food[]>(`/nutrition/foods/search?q=${encodeURIComponent(q)}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getFoodByBarcode: (token: string, digits: string) =>
    request<Food>(`/nutrition/foods/barcode/${encodeURIComponent(digits)}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  createFood: (token: string, body: FoodInput) =>
    request<Food>("/nutrition/foods", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  addMealEntry: (token: string, body: MealEntryInput) =>
    request<MealEntry>("/nutrition/meals", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  updateMealEntry: (
    token: string,
    id: string,
    body: { meal?: MealName; grams?: number; note?: string },
  ) =>
    request<MealEntry>(`/nutrition/meals/${id}`, {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteMealEntry: (token: string, id: string) =>
    request<void>(`/nutrition/meals/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  parseMeal: (token: string, text: string) =>
    request<ParseMealResult>("/nutrition/meals/parse", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ text }),
    }),
  saveMealBatch: (
    token: string,
    body: { eatenOn: string; meal: MealName; items: ProposedItem[]; method?: string },
  ) =>
    request<MealEntry[]>("/nutrition/meals/batch", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  getNutritionDay: (token: string, day: string) =>
    request<NutritionDay>(`/nutrition/day?day=${day}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getNutritionWeek: (token: string, end: string) =>
    request<NutritionWeek>(`/nutrition/week?end=${end}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  getNutritionGoal: (token: string) =>
    request<NutritionGoal>("/nutrition/goal", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  saveNutritionGoal: (token: string, body: NutritionGoal) =>
    request<NutritionGoal>("/nutrition/goal", {
      method: "PUT",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  getWeight: (token: string, days = 90) =>
    request<WeightSeries>(`/nutrition/weight?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    }),
  addWeight: (token: string, body: { measuredOn: string; weightKg: number }) =>
    request<WeightSeries>("/nutrition/weight", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteWeight: (token: string, day: string) =>
    request<void>(`/nutrition/weight/${day}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  listMealTemplates: (token: string) =>
    request<MealTemplate[]>("/nutrition/templates", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  createMealTemplate: (
    token: string,
    body: { name: string; items: { foodId: string; grams: number }[] },
  ) =>
    request<MealTemplate>("/nutrition/templates", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  deleteMealTemplate: (token: string, id: string) =>
    request<void>(`/nutrition/templates/${id}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    }),
  applyMealTemplate: (
    token: string,
    id: string,
    body: { eatenOn: string; meal: MealName },
  ) =>
    request<MealEntry[]>(`/nutrition/templates/${id}/apply`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
};
