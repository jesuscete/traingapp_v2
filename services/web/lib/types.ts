export type Exercise = {
  id: string;
  name: string;
  sets: number | null;
  reps: number | null;
  weightKg: number | null;
  durationMinutes: number | null;
  distanceMeters: number | null;
  volumeKg: number;
};

export type CombatBlockType =
  | "saco"
  | "sparring"
  | "manoplas"
  | "comba"
  | "sombra"
  | "tecnica"
  | "fisico";

export type CombatBlock = {
  type: CombatBlockType;
  rounds?: number | null;
  roundSeconds?: number | null;
  minutes?: number | null;
  strikes?: number | null;
};

export type ClimbingStyle = "boulder" | "via" | "autobelay" | "exterior";

export type ClimbingRoute = {
  grade: string;
  attempts?: number | null;
  sent: boolean;
};

export type CombatMetrics = { kind: "combat"; blocks: CombatBlock[] };
export type EnduranceMetrics = {
  kind: "endurance";
  distanceMeters?: number | null;
  avgHeartRate?: number | null;
  maxHeartRate?: number | null;
  elevationGainM?: number | null;
};
export type ClimbingMetrics = {
  kind: "climbing";
  style: ClimbingStyle;
  routes: ClimbingRoute[];
};
export type GenericMetrics = { kind: "generic"; notes?: string | null };

export type SessionMetrics =
  | CombatMetrics
  | EnduranceMetrics
  | ClimbingMetrics
  | GenericMetrics;

export type SessionIn = {
  discipline: string;
  rawText: string;
  performedAt: string;
  durationMinutes?: number;
  intensity?: number;
  note?: string;
  metrics?: SessionMetrics;
  exercises: [];
};

export type SessionUpdate = {
  rawText?: string;
  performedAt?: string;
  durationMinutes?: number;
  intensity?: number;
  fatigue?: number;
  note?: string;
  metrics?: SessionMetrics;
};

export type FatigueExplainItem = {
  sessionId: string;
  performedOn: string;
  discipline: string;
  label: string;
  impulse: number;
  remaining: number;
  share: number;
};

export type FatigueExplain = {
  group: string;
  fatigue: number;
  sessions: FatigueExplainItem[];
};

export type SessionDetails = {
  metrics?: SessionMetrics | null;
  rpe?: number | null;
  perceivedFatigue?: number | null;
  [key: string]: unknown;
};

export type Session = {
  id: string;
  discipline: string;
  rawText: string;
  performedAt: string;
  durationMinutes: number | null;
  distanceMeters?: number | null;
  volumeKg: number;
  estimatedKcal: number | null;
  intensity?: number | null;
  fatigue?: number | null;
  note: string | null;
  createdAt: string;
  exercises: Exercise[];
  details?: SessionDetails | null;
  muscleImpacts?: MuscleImpact[];
};

export type MuscleImpact = {
  muscleGroup: string;
  activation: number;
  zone?: string;
};

export type SetEntry = {
  id: string;
  entryOrder: number;
  reps: number | null;
  weight: number | null;
  weightUnit: string;
  durationSeconds: number | null;
  distanceMeters: number | null;
  rpe: number | null;
  side: string;
};

export type WorkoutSet = {
  id: string;
  setNumber: number;
  setType: string;
  restSeconds: number | null;
  isWarmup: boolean;
  volumeKg: number;
  entries: SetEntry[];
};

export type WorkoutExercise = {
  id: string;
  sessionId: string;
  exerciseId: string | null;
  name: string;
  orderIndex: number;
  supersetGroupId: string | null;
  volumeKg: number;
  sets: WorkoutSet[];
};

export type WorkoutSessionSummary = {
  sessionId: string;
  totalVolume: number;
  avgRpe: number | null;
  setsCount: number;
  durationMin: number;
};

export type GymSession = {
  id: string;
  discipline: string;
  rawText: string;
  performedAt: string;
  startTime: string | null;
  endTime: string | null;
  intensity: number | null;
  fatigue: number | null;
  durationMinutes: number | null;
  volumeKg: number;
  estimatedKcal: number | null;
  calories: number | null;
  note: string | null;
  details: SessionDetails | null;
  createdAt: string;
  workoutExercises: WorkoutExercise[];
  summary: WorkoutSessionSummary | null;
  muscleImpacts: MuscleImpact[];
};

export type ExerciseDraft = {
  name: string;
  sets: number | null;
  reps: number | null;
  perSetReps?: number[] | null;
  weightKg: number | null;
};

export type WorkoutDraft = {
  rawText: string;
  discipline: string;
  performedAt: string;
  durationMinutes: number | null;
  exercises: ExerciseDraft[];
  suggestedRpe: number | null;
  confidence: number;
  unresolved: string[];
  metrics?: SessionMetrics | null;
};

export type PlanSplit = {
  id: string;
  name: string;
  description: string;
};

export type PlanSetTarget = {
  targetRepsMin: number;
  targetRepsMax: number | null;
  targetRestSeconds: number | null;
};

export type PlanExercise = {
  name: string;
  exerciseId: string | null;
  sets: PlanSetTarget[];
};

export type PlanDay = {
  dayOfWeek: number;
  dayType: "gimnasio" | "deporte" | "descanso";
  label: string | null;
  disciplineId: string | null;
  disciplineName: string | null;
  durationMin: number | null;
  exercises: PlanExercise[];
};

export type PlanSummary = {
  name: string;
  days: PlanDay[];
};

export type ChatMessageOut = {
  mode: "direct" | "live" | "confirm" | "routine" | "plan";
  requestId?: string | null;
  liveSessionId?: string | null;
  startedAt?: string | null;
  entriesCount: number;
  draft?: WorkoutDraft | null;
  message?: string | null;
  splits?: PlanSplit[] | null;
  plan?: PlanSummary | null;
  planStatus?: string | null;
};

export type User = {
  id: string;
  email: string;
  name: string;
  weightKg: number | null;
  heightCm: number | null;
  birthYear: number | null;
  sex: string | null;
  goal: string | null;
  sports: string[] | null;
};

export type Energy = {
  weightKg: number | null;
  heightCm: number | null;
  age: number | null;
  goal: string | null;
  bmrKcal: number | null;
  tdeeKcal: number | null;
  targetKcal: number | null;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: User;
};

export type ChatEnqueue = {
  requestId: string;
  status: string;
};

export type DisciplineTotal = {
  discipline: string;
  sessions: number;
  volumeKg: number;
  durationMinutes: number;
};

export type WeeklyVolume = {
  start: string;
  sessions: number;
  volumeKg: number;
};

export type StatsOverview = {
  periodDays: number;
  totalSessions: number;
  totalVolumeKg: number;
  totalDurationMinutes: number;
  sessionsPerWeek: number;
  byDiscipline: DisciplineTotal[];
  weeklyVolume: WeeklyVolume[];
};

export type MuscleGroupVolume = {
  muscleGroup: string;
  volumeKg: number;
  sessions: number;
  topExercises: { name: string; volumeKg: number; sets: number }[];
  zone?: string;
};

export type ExerciseProgress = {
  exercise: string;
  best1Rm: number | null;
  first1Rm: number | null;
  deltaPct: number | null;
  sessions: number;
};

export type StatsVolume = {
  periodDays: number;
  totalVolumeKg: number;
  unclassifiedVolumeKg: number;
  byMuscleGroup: MuscleGroupVolume[];
  exerciseProgress: ExerciseProgress[];
};

export type CardioDiscipline = {
  discipline: string;
  sessions: number;
  durationMinutes: number;
  distanceMeters: number | null;
  avgDurationMinutes: number;
};

export type StatsCardio = {
  periodDays: number;
  totalDurationMinutes: number;
  totalDistanceMeters: number | null;
  byDiscipline: CardioDiscipline[];
};

export type Insight = {
  kind: string;
  severity: string;
  message: string;
};

export type PeriodTotals = {
  sessions: number;
  volumeKg: number;
  durationMinutes: number;
};

export type StatsProgress = {
  periodDays: number;
  current: PeriodTotals;
  previous: PeriodTotals;
  volumeDeltaPct: number | null;
  sessionDeltaPct: number | null;
  insights: Insight[];
};

export type FatigueMuscle = {
  muscleGroup: string;
  fatigue: number;
  impulseToday: number;
  level: "ok" | "warning" | "danger";
  acwr: number;
  zone?: string;
};

export type FatigueRisk = {
  muscleGroup: string;
  level: string;
  reasons: string[];
};

export type Readiness = {
  date: string;
  sleepHours: number | null;
  doms: number | null;
  restDay: boolean;
};

export type Fatigue = {
  asOf: string;
  projected: string;
  muscles: FatigueMuscle[];
  maxFatigue: number;
  avgFatigue: number;
  readiness: Readiness | null;
  risks: FatigueRisk[];
};

export type FatigueSeriesMuscle = {
  muscleGroup: string;
  fatigue: number;
  zone?: string;
};

export type FatigueSeriesDay = {
  date: string;
  maxFatigue: number;
  avgFatigue: number;
  muscles: FatigueSeriesMuscle[];
};

export type FatigueSeries = {
  periodDays: number;
  series: FatigueSeriesDay[];
};

export type LoadMuscle = {
  muscleGroup: string;
  accumulatedLoad: number;
  recovery: number;
  trend: string;
  zone?: string;
};

export type Load = {
  periodDays: number;
  totalLoad: number;
  monotony: number;
  strain: number;
  byMuscleGroup: LoadMuscle[];
};

export type SessionSummary = {
  id: string;
  discipline: string;
  rawText: string;
  performedAt: string;
  durationMinutes: number | null;
  volumeKg: number;
  estimatedKcal: number | null;
};

export type SessionPage = {
  items: SessionSummary[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
};

export type DisciplineStat = {
  discipline: string;
  sessions: number;
  durationMinutes: number;
  volumeKg: number;
  estimatedKcal: number;
};

export type DisciplineDelta = {
  discipline: string;
  sessions: number;
  deltaPct: number | null;
};

export type SummaryHighlights = {
  totalSessions: number;
  totalDurationMinutes: number;
  totalVolumeKg: number;
  totalKcal: number;
};

export type HistorySummary = {
  days: number;
  highlights: SummaryHighlights;
  byDiscipline: DisciplineStat[];
  deltas: DisciplineDelta[];
  recent: SessionSummary[];
};

export type DayType = "gimnasio" | "deporte" | "descanso";

export type RoutineSet = {
  id: string;
  setNumber: number;
  setType: string;
  targetRepsMin: number | null;
  targetRepsMax: number | null;
  targetRestSeconds: number | null;
};

export type RoutineExercise = {
  id: string;
  exerciseId: string | null;
  name: string | null;
  orderIndex: number;
  supersetGroupId: string | null;
  notes: string | null;
  sets: RoutineSet[];
};

export type RoutineDay = {
  id: string;
  dayOfWeek: number;
  dayType: DayType;
  label: string | null;
  disciplineId: string | null;
  disciplineName: string | null;
  targetDurationMin: number | null;
  notes: string | null;
  exercises: RoutineExercise[];
};

export type Routine = {
  id: string;
  name: string;
  isActive: boolean;
  createdAt: string;
  days: RoutineDay[];
};

export type RoutineDayInput = {
  dayOfWeek: number;
  dayType: DayType;
  label?: string | null;
  disciplineId?: string | null;
  targetDurationMin?: number | null;
  notes?: string | null;
  exercises?: RoutineExerciseInput[];
};

export type RoutineExerciseInput = {
  exerciseId: string;
  orderIndex?: number;
  supersetGroupId?: string | null;
  notes?: string | null;
  sets: RoutineSetInput[];
};

export type RoutineSetInput = {
  setNumber: number;
  setType: string;
  targetRepsMin: number | null;
  targetRepsMax?: number | null;
  targetRestSeconds?: number | null;
};

export type RoutineInput = {
  name: string;
  days: RoutineDayInput[];
};

export type RoutineReviewItem = {
  diaSemana: string;
  tipo: DayType;
  nombre: string;
  gruposMusculares: string[];
  series: number;
  repeticiones: number | null;
  duracionMin: number | null;
};

export type RoutineReviewInput = {
  routineName: string;
  days: RoutineReviewItem[];
};

export type Solapamiento = {
  descripcion: string;
  grupos: string[];
  dias: string[];
};

export type RoutineReview = {
  source?: "llm" | "fallback";
  puntosFuertes: string[];
  solapamientos: Solapamiento[];
  sugerencias: string[];
};

export type Discipline = {
  id: string;
  name: string;
  normalizedName: string;
  met: number;
  category: string;
  kind: 'gym' | 'cardio';
  muscleLoads: { muscleGroup: string; load: number }[];
};

export type CatalogExerciseDetails = {
  source?: string;
  sourceId?: string;
  category?: string;
  force?: string | null;
  level?: string;
  mechanic?: string | null;
  equipment?: string;
  instructions?: string[];
  nameEs?: string;
  instructionsEs?: string[];
};

export type CatalogExercise = {
  id: string;
  name: string;
  normalizedName: string;
  exerciseType: string;
  muscleMap: Record<string, number>;
  usesBodyweight: boolean;
  unilateral: boolean;
  images: string[];
  imageUrls: string[];
  isFavorite: boolean;
  isCustom?: boolean;
  details: CatalogExerciseDetails | null;
};

export type MuscleGroupKey =
  | "back"
  | "biceps"
  | "calves"
  | "chest"
  | "core"
  | "forearms"
  | "glutes"
  | "hamstrings"
  | "neck"
  | "quadriceps"
  | "shoulders"
  | "triceps";

export type CustomExerciseInput = {
  name: string;
  primaryMuscles: MuscleGroupKey[];
  secondaryMuscles?: MuscleGroupKey[];
  equipment?: string | null;
  category?: string;
  usesBodyweight?: boolean;
  unilateral?: boolean;
  instructions?: string[];
};

export type ExerciseRecords = {
  maxWeightKg: number | null;
  bestE1rmKg: number | null;
  maxReps: number | null;
  bestSetVolumeKg: number | null;
  bestSessionVolumeKg: number | null;
};

export type ExerciseProgressPoint = {
  performedAt: string;
  bestE1rmKg: number | null;
  topWeightKg: number | null;
  volumeKg: number | null;
};

export type ExerciseHistorySet = {
  setNumber: number;
  setType: string;
  isWarmup: boolean;
  reps: number | null;
  weightKg: number | null;
  rpe: number | null;
  e1rmKg: number | null;
};

export type ExerciseHistorySession = {
  sessionId: string;
  performedAt: string;
  sets: ExerciseHistorySet[];
};

export type ExerciseHistory = {
  exerciseId: string;
  records: ExerciseRecords;
  progress: ExerciseProgressPoint[];
  sessions: ExerciseHistorySession[];
};

export type GymSetType =
  | "normal"
  | "calentamiento"
  | "dropset"
  | "al_fallo"
  | "amrap"
  | "isometrico";

export type GymSetEntryIn = {
  entryOrder: number;
  reps?: number | null;
  weight?: number | null;
  weightUnit: "kg";
  rpe?: number | null;
  side: "both";
  durationSeconds?: number | null;
};

export type GymSetIn = {
  setNumber: number;
  setType: GymSetType;
  restSeconds?: number | null;
  isWarmup: boolean;
  entries: GymSetEntryIn[];
};

export type GymExerciseIn = {
  exerciseId?: string | null;
  name: string;
  orderIndex: number;
  supersetGroupId?: string | null;
  sets: GymSetIn[];
};

export type GymSessionIn = {
  clientId?: string | null;
  rawText: string;
  performedAt: string;
  startTime?: string | null;
  endTime?: string | null;
  durationMinutes?: number | null;
  intensity?: number | null;
  note?: string | null;
  routineDayId?: string | null;
  exercises: GymExerciseIn[];
};

export type LiveSet = {
  setNumber: number;
  setType: string;
  targetRepsMin: number | null;
  targetRepsMax: number | null;
  reps: number | null;
  weight: number | null;
  suggestedWeight: number | null;
  isWarmup: boolean;
};

export type LiveExercise = {
  name: string;
  exerciseId: string | null;
  orderIndex: number;
  routineExerciseId: string | null;
  sets: LiveSet[];
};

export type LiveSession = {
  liveSessionId: string;
  startedAt: string;
  origin: "free" | "routine";
  discipline: string | null;
  routineDayId: string | null;
  exercises: LiveExercise[];
  entries: string[];
  entriesCount: number;
};

/* ===== M4 deporte y entrenador ===== */

export type GapSeverity = "alta" | "media" | "baja";
export type TargetStatus = "missing" | "low" | "ok" | "high";
export type SportBasis = "historial" | "rutina" | "sin_datos";

export type SportTarget = {
  key: string;
  label: string;
  value: number;
  low: number;
  high: number | null;
  status: TargetStatus;
};

export type SportSuggestion = {
  exerciseId: string;
  name: string;
  imageUrl: string | null;
};

export type SportGap = {
  code: string;
  severity: GapSeverity;
  message: string;
  suggestions: SportSuggestion[];
};

export type SportNarrative = {
  source: "llm" | "fallback";
  resumen: string;
  prioridades: string[];
};

export type SportAnalysis = {
  sport: string;
  label: string;
  basis: SportBasis;
  weeks: number;
  score: number;
  patterns: SportTarget[];
  muscles: SportTarget[];
  repZones: SportTarget[];
  pushSets: number;
  pullSets: number;
  pullPushRatio: number | null;
  gaps: SportGap[];
  narrative: SportNarrative | null;
};

export type ExerciseAlternative = {
  exerciseId: string;
  name: string;
  similarity: number;
  imageUrl: string | null;
  isCustom: boolean;
};

export type AgentActionType = "save_workout" | "swap_exercise" | "add_exercise";

export type AgentAction = {
  id: string;
  type: AgentActionType;
  summary: string;
  requestId: string | null;
};

export type AgentReply = {
  source: "llm" | "fallback";
  reply: string;
  actions: AgentAction[];
  toolsUsed: string[];
};
