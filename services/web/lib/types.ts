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

export type Session = {
  id: string;
  discipline: string;
  rawText: string;
  performedAt: string;
  durationMinutes: number | null;
  volumeKg: number;
  estimatedKcal: number | null;
  note: string | null;
  createdAt: string;
  exercises: Exercise[];
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
