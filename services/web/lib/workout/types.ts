import type { ExerciseRecords, GymSession, GymSessionIn } from "@/lib/types";

export type WorkoutSetType = "normal" | "calentamiento" | "dropset" | "al_fallo";

export const SET_TYPE_CYCLE: WorkoutSetType[] = [
  "normal",
  "calentamiento",
  "dropset",
  "al_fallo",
];

export type PreviousSet = { weightKg: number | null; reps: number | null };

export type WorkoutSet = {
  id: string;
  type: WorkoutSetType;
  weight: string;
  reps: string;
  rpe: string;
  done: boolean;
  targetRepsMin: number | null;
  targetRepsMax: number | null;
};

export type HistoryState = "pending" | "loaded";

export type WorkoutExercise = {
  id: string;
  exerciseId: string | null;
  name: string;
  imageUrl: string | null;
  note: string;
  supersetGroupId: string | null;
  restSeconds: number;
  sets: WorkoutSet[];
  previous: PreviousSet[];
  records: ExerciseRecords | null;
  history: HistoryState;
};

export type RestState = { endsAt: number; total: number };

export type ActiveWorkout = {
  version: 1;
  id: string;
  title: string;
  startedAt: number;
  routineDayId: string | null;
  exercises: WorkoutExercise[];
  rest: RestState | null;
};

export type PersonalRecord = {
  exerciseName: string;
  kind: "peso" | "1rm";
  value: number;
};

export type PendingWorkout = {
  clientId: string;
  savedAt: number;
  payload: GymSessionIn;
};

export type WorkoutResult = {
  session: GymSession | null;
  title: string;
  durationMin: number;
  volumeKg: number;
  setsCount: number;
  prs: PersonalRecord[];
  queued: boolean;
};

export const DEFAULT_REST_SECONDS = 90;
