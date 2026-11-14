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

export type WodFormat =
  | "for_time"
  | "amrap"
  | "emom"
  | "tabata"
  | "intervals"
  | "strength"
  | "hyrox_sim"
  | "hyrox_race"
  | "other";
export type HyroxCategory = "open_men" | "open_women" | "pro_men" | "pro_women" | "doubles" | "relay";
export type WodMovement = {
  exerciseId?: string | null;
  name: string;
  reps?: number | null;
  weightKg?: number | null;
  distanceM?: number | null;
  calories?: number | null;
};
export type WodSplit = { name: string; seconds: number };
export type WodMetrics = {
  kind: "wod";
  format: WodFormat;
  name?: string | null;
  scheme?: string | null;
  timeCapMinutes?: number | null;
  timeSeconds?: number | null;
  rounds?: number | null;
  extraReps?: number | null;
  totalReps?: number | null;
  loadKg?: number | null;
  rx?: boolean;
  hyroxCategory?: HyroxCategory | null;
  movements?: WodMovement[];
  splits?: WodSplit[];
};

export type SessionMetrics =
  | CombatMetrics
  | EnduranceMetrics
  | ClimbingMetrics
  | WodMetrics
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
  birthDate?: string | null;
  onboardingSkipped?: string[] | null;
  sex: string | null;
  goal: string | null;
  sports: string[] | null;
  primarySport?: string | null;
  maxHr?: number | null;
  restingHr?: number | null;
  fitnessLevel?: string | null;
  equipment?: UserEquipment | null;
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
  refresh_token: string;
  expires_in: number;
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
  distanceMeters?: number | null;
  externalSource?: string | null;
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
  /** Movimientos de CrossFit/HYROX: cómo se miden. */
  unit?: "reps" | "distance" | "calories";
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
  equipment?: string | null;
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
  adherence?: RoutineAdherence | null;
};

export type ExerciseAdherence = {
  exerciseId: string | null;
  name: string;
  plannedSetsWeek: number;
  doneSetsWeek: number;
};

/** Rutina frente a lo registrado de verdad. */
export type RoutineAdherence = {
  weeks: number;
  pct: number;
  sessions: number;
  historyScore: number | null;
  skipped: ExerciseAdherence[];
  offPlan: ExerciseAdherence[];
};

export type WeekFeedback = {
  headline: string;
  message: string;
  score: number | null;
  focusCode: string | null;
};

export type ExerciseAlternative = {
  exerciseId: string;
  name: string;
  similarity: number;
  imageUrl: string | null;
  isCustom: boolean;
  equipment?: string | null;
  equipmentLabel?: string | null;
  reason?: string | null;
  sameCondition?: boolean;
};

/* ===== M10: material del usuario ===== */
export type EquipmentCode =
  | "barbell"
  | "e-z curl bar"
  | "dumbbell"
  | "kettlebells"
  | "cable"
  | "machine"
  | "bands"
  | "medicine ball"
  | "exercise ball"
  | "foam roll"
  | "body only"
  | "other";
export type EquipmentPreset = "gimnasio" | "casa" | "sin_material";
export type UserEquipment = {
  preset: EquipmentPreset;
  extra: EquipmentCode[];
  missing: EquipmentCode[];
};

export type AgentActionType = "save_workout" | "swap_exercise" | "add_exercise" | "save_meal";

export type AgentAction = {
  id: string;
  type: AgentActionType;
  summary: string;
  requestId: string | null;
};

/* ===== M10: tarjetas del chat (respuestas sin IA) ===== */
export type ChatCardItem = {
  title: string;
  subtitle?: string | null;
  badge?: string | null;
  detail?: string | null;
  imageUrl?: string | null;
  exerciseId?: string | null;
  value?: number | null;
};

export type ChatCardSection = { title?: string | null; items: ChatCardItem[] };

export type ChatCard = {
  type: "routine" | "fatigue" | "exercises" | "nutrition";
  title: string;
  subtitle?: string | null;
  sections: ChatCardSection[];
  link?: string | null;
  linkLabel?: string | null;
};

export type AgentReply = {
  source: "llm" | "fallback" | "rules";
  reply: string;
  actions: AgentAction[];
  toolsUsed: string[];
  cards?: ChatCard[];
  handoff?: "guided" | null;
};

/* ===== M5 nutrición ===== */
export type MealName = "desayuno" | "media_manana" | "comida" | "merienda" | "cena" | "dia";
export type MealMethod = "pesada" | "etiqueta" | "racion" | "rapida" | "ia";
export type FoodSource = "off" | "usda" | "custom" | "ia";
export type GoalType = "perder" | "mantener" | "ganar" | "corte";

export type Serving = { label: string; grams: number };

export type FoodFacets = { stores: string[]; brands: string[] };

export type Food = {
  id: string;
  source: FoodSource;
  name: string;
  brand: string | null;
  /** Supermercado de origen si viene de una importación por tienda (p. ej. "Lidl"). */
  store?: string | null;
  barcode: string | null;
  kcal100g: number;
  protein100g: number;
  carbs100g: number;
  fat100g: number;
  fiber100g: number | null;
  sugar100g: number | null;
  servings: Serving[];
  isCustom: boolean;
};

export type FoodInput = {
  name: string;
  brand?: string | null;
  barcode?: string | null;
  kcal100g: number;
  protein100g: number;
  carbs100g: number;
  fat100g: number;
  fiber100g?: number | null;
  sugar100g?: number | null;
  servings?: Serving[];
};

export type MealEntryInput = {
  eatenOn: string;
  meal: MealName;
  foodId?: string;
  grams?: number;
  servings?: number;
  servingLabel?: string;
  name?: string;
  kcal?: number;
  proteinG?: number;
  carbsG?: number;
  fatG?: number;
  method?: MealMethod;
  note?: string;
};

export type MealEntry = {
  id: string;
  eatenOn: string;
  meal: string;
  foodId: string | null;
  name: string;
  grams: number | null;
  kcal: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
  fiberG: number | null;
  method: string;
  note: string | null;
};

export type ProposedItem = {
  name: string;
  grams: number;
  kcal100g: number;
  protein100g: number;
  carbs100g: number;
  fat100g: number;
  fiber100g: number | null;
  source: "usda" | "ia" | "custom" | "off";
  foodId: string | null;
  /** Frase del diccionario de comidas (M10): si cambias los gramos, se recuerda tu ración. */
  alias?: string | null;
  quantity?: number | null;
};

export type ParseMealResult = {
  items: ProposedItem[];
  unresolved: string[];
  /** "rules" = todo salió del diccionario, sin IA. */
  source: "llm" | "fallback" | "rules";
};

export type NutritionTotals = {
  kcal: number;
  proteinG: number;
  carbsG: number;
  fatG: number;
  fiberG: number;
};

export type NutritionTarget = {
  bmr: number;
  dailyActivityKcal: number;
  trainingKcal: number;
  maintenanceKcal: number;
  adjustmentKcal: number;
  targetKcal: number;
  proteinG: number;
  fatG: number;
  carbsG: number;
  fiberG: number;
  rateKgWeek: number;
  notes: string[];
  activityMode?: ActivityMode;
};

export type NutritionDay = {
  day: string;
  meals: Record<string, MealEntry[]>;
  totals: NutritionTotals;
  exactKcal: number;
  estimatedKcal: number;
  target: NutritionTarget | null;
  missingProfile: string[];
  weightKg: number | null;
};

export type NutritionWeek = {
  days: { day: string; kcal: number; proteinG: number; targetKcal: number | null }[];
  averageKcal: number;
  averageTargetKcal: number | null;
};

export type NutritionGoal = {
  goal: GoalType;
  targetWeightKg?: number | null;
  targetDate?: string | null;
  rateKgWeek?: number | null;
  proteinGPerKg: number;
  activityFactor: number;
  activityMode?: ActivityMode;
};

export type WeightPoint = {
  measuredOn: string;
  weightKg: number;
  bodyFatPct?: number | null;
  musclePct?: number | null;
};

export type WeightSeries = {
  points: WeightPoint[];
  latestKg: number | null;
  average7dKg: number | null;
  changeWeekKg: number | null;
  latestBodyFatPct?: number | null;
  latestMusclePct?: number | null;
};

export type WeightInput = {
  measuredOn: string;
  weightKg: number;
  bodyFatPct?: number;
  musclePct?: number;
};

export type MealTemplate = {
  id: string;
  name: string;
  items: { foodId: string; grams: number }[];
  kcal: number;
};

/* ===== M6 actividades ===== */
export type ImportStatus = "imported" | "duplicate" | "overlap" | "error";

export type ImportResult = {
  filename: string;
  status: ImportStatus;
  message: string;
  sessionId: string | null;
  discipline: string | null;
  suggestedMaxHr: number | null;
};

export type KmSplit = {
  km: number;
  seconds: number;
  paceSPerKm: number;
  avgHr: number | null;
};

export type ActivitySummary = {
  source: string;
  /** Datos del reloj (más fiables que recalcularlos desde las muestras). */
  distanceM?: number | null;
  durationS?: number | null;
  ascentM?: number | null;
  sport: string | null;
  subSport: string | null;
  avgHr: number | null;
  maxHr: number | null;
  avgCadence: number | null;
  deviceCalories: number | null;
  trimp: number | null;
  zonesSeconds: number[] | null;
  zoneBounds: [number, number][];
  hrProfile: {
    maxHr: number;
    restingHr: number;
    maxEstimated: boolean;
    restingEstimated: boolean;
  };
  kmSplits: KmSplit[];
  laps: number;
};

export type ActivitySamples = {
  t?: number[];
  hr?: (number | null)[];
  speed?: (number | null)[];
  altitude?: (number | null)[];
  cadence?: (number | null)[];
  power?: (number | null)[];
  distance?: (number | null)[];
  lat?: (number | null)[];
  lon?: (number | null)[];
};

export type ActivityLap = {
  start_s: number;
  duration_s: number;
  distance_m: number | null;
  avg_hr: number | null;
  max_hr: number | null;
};

export type ActivityDetail = {
  sessionId: string;
  discipline: string;
  summary: ActivitySummary | null;
  samples: ActivitySamples;
  laps: ActivityLap[];
};

export type HomeInsight = {
  kind: "good" | "warning" | "rest" | "tip";
  title: string;
  detail: string;
  href: string | null;
};

export type HomeSportWeek = {
  discipline: string;
  sessions: number;
  minutes: number;
  distanceM: number;
};

export type HomeSummary = {
  insights: HomeInsight[];
  daysSinceLast: number | null;
  weekSessions: number;
  weekMinutes: number;
  prevWeekMinutes: number;
  weekBySport: HomeSportWeek[];
  activeDays: string[];
  sport?: string;
  sportLabel?: string;
  primaryGoal?: Goal | null;
};

/* ===== Objetivos ===== */
export type GoalKind = "weight" | "event" | "competition" | "performance" | "other";

export type GoalIn = {
  kind: GoalKind;
  title: string;
  sport?: string | null;
  targetDate?: string | null;
  targetValue?: number | null;
  unit?: string | null;
  notes?: string | null;
  isPrimary?: boolean;
  done?: boolean;
};

export type Goal = GoalIn & { id: string; daysLeft: number | null };

export type GarminStatus = {
  connected: boolean;
  status: string | null;
  lastSyncAt: string | null;
  lastError: string | null;
  lastResult: { imported?: number; skipped?: number; errors?: number; healthDays?: number } | null;
  tokenExpiresAt: string | null;
};

export type GarminSyncResult = {
  imported: number;
  skipped: number;
  errors: number;
  healthDays: number;
  messages: string[];
  status: GarminStatus;
};

export type OnboardingStep = {
  key: string;
  label: string;
  done: boolean;
  skipped: boolean;
  href: string | null;
};

export type Onboarding = {
  complete: boolean;
  required: OnboardingStep[];
  recommended: OnboardingStep[];
  pendingRecommended: number;
};

/** registro: factor sin deporte + entrenos reales. estimado: factor con deporte incluido. */
export type ActivityMode = "registro" | "estimado";
