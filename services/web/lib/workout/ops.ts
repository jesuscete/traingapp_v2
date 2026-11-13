import type {
  CatalogExercise,
  ExerciseHistory,
  Routine,
  RoutineDay,
} from "@/lib/types";
import { exerciseDisplayName } from "@/lib/exerciseSearch";
import {
  DEFAULT_REST_SECONDS,
  SET_TYPE_CYCLE,
  type ActiveWorkout,
  type PreviousSet,
  type WorkoutExercise,
  type WorkoutSet,
  type WorkoutSetType,
} from "@/lib/workout/types";

/**
 * UUID v4. `crypto.randomUUID` solo existe en contextos seguros (HTTPS/localhost);
 * desde el móvil por http://IP-LAN no está, así que se construye con getRandomValues
 * (disponible siempre). El backend exige UUID en clientId y supersetGroupId.
 */
export function uid(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function parseNum(value: string): number | null {
  const parsed = Number(value.replace(",", "."));
  return value.trim() === "" || Number.isNaN(parsed) ? null : parsed;
}

function newSet(patch: Partial<WorkoutSet> = {}): WorkoutSet {
  return {
    id: uid(),
    type: "normal",
    weight: "",
    reps: "",
    rpe: "",
    done: false,
    targetRepsMin: null,
    targetRepsMax: null,
    ...patch,
  };
}

export function newWorkout(
  title: string,
  routineDayId: string | null,
  exercises: WorkoutExercise[],
): ActiveWorkout {
  return {
    version: 1,
    id: uid(),
    title,
    startedAt: Date.now(),
    routineDayId,
    exercises,
    rest: null,
  };
}

export function exerciseFromCatalog(ex: CatalogExercise, sets = 3): WorkoutExercise {
  return {
    id: uid(),
    exerciseId: ex.id,
    name: exerciseDisplayName(ex),
    imageUrl: ex.imageUrls[0] ?? null,
    note: "",
    supersetGroupId: null,
    restSeconds: DEFAULT_REST_SECONDS,
    sets: Array.from({ length: sets }, () => newSet()),
    previous: [],
    records: null,
    history: "pending",
  };
}

function toSetType(value: string): WorkoutSetType {
  return (SET_TYPE_CYCLE as string[]).includes(value) ? (value as WorkoutSetType) : "normal";
}

export function exercisesFromRoutineDay(
  day: RoutineDay,
  catalog: CatalogExercise[],
): WorkoutExercise[] {
  const byId = new Map(catalog.map((ex) => [ex.id, ex]));
  return [...day.exercises]
    .sort((a, b) => a.orderIndex - b.orderIndex)
    .map((re) => {
      const cat = re.exerciseId ? byId.get(re.exerciseId) : undefined;
      const sets = [...re.sets]
        .sort((a, b) => a.setNumber - b.setNumber)
        .map((s) =>
          newSet({
            type: toSetType(s.setType),
            targetRepsMin: s.targetRepsMin,
            targetRepsMax: s.targetRepsMax,
          }),
        );
      const rest = re.sets.find((s) => s.targetRestSeconds)?.targetRestSeconds;
      return {
        id: uid(),
        exerciseId: re.exerciseId,
        name: cat ? exerciseDisplayName(cat) : (re.name ?? "Ejercicio"),
        imageUrl: cat?.imageUrls[0] ?? null,
        note: re.notes ?? "",
        supersetGroupId: re.supersetGroupId,
        restSeconds: rest ?? DEFAULT_REST_SECONDS,
        sets: sets.length > 0 ? sets : [newSet()],
        previous: [],
        records: null,
        history: re.exerciseId ? ("pending" as const) : ("loaded" as const),
      };
    });
}

export function routineDayTitle(routine: Routine, day: RoutineDay, weekday: string): string {
  return day.label?.trim() || `${routine.name} · ${weekday}`;
}

function mapEx(
  w: ActiveWorkout,
  exId: string,
  fn: (ex: WorkoutExercise) => WorkoutExercise,
): ActiveWorkout {
  return { ...w, exercises: w.exercises.map((ex) => (ex.id === exId ? fn(ex) : ex)) };
}

function mapSet(
  w: ActiveWorkout,
  exId: string,
  setId: string,
  fn: (s: WorkoutSet) => WorkoutSet,
): ActiveWorkout {
  return mapEx(w, exId, (ex) => ({
    ...ex,
    sets: ex.sets.map((s) => (s.id === setId ? fn(s) : s)),
  }));
}

/** Un grupo de superserie con un solo miembro deja de serlo. */
function normalizeSupersets(exercises: WorkoutExercise[]): WorkoutExercise[] {
  const counts = new Map<string, number>();
  for (const ex of exercises) {
    if (ex.supersetGroupId) {
      counts.set(ex.supersetGroupId, (counts.get(ex.supersetGroupId) ?? 0) + 1);
    }
  }
  return exercises.map((ex) =>
    ex.supersetGroupId && (counts.get(ex.supersetGroupId) ?? 0) < 2
      ? { ...ex, supersetGroupId: null }
      : ex,
  );
}

export function addExercises(w: ActiveWorkout, list: WorkoutExercise[]): ActiveWorkout {
  return { ...w, exercises: [...w.exercises, ...list] };
}

export function removeExercise(w: ActiveWorkout, exId: string): ActiveWorkout {
  return { ...w, exercises: normalizeSupersets(w.exercises.filter((ex) => ex.id !== exId)) };
}

export function moveExercise(w: ActiveWorkout, exId: string, dir: -1 | 1): ActiveWorkout {
  const i = w.exercises.findIndex((ex) => ex.id === exId);
  const j = i + dir;
  if (i < 0 || j < 0 || j >= w.exercises.length) return w;
  const exercises = [...w.exercises];
  [exercises[i], exercises[j]] = [exercises[j], exercises[i]];
  return { ...w, exercises: normalizeSupersets(exercises) };
}

/** Agrupa o separa el ejercicio con el siguiente. */
export function toggleSupersetWithNext(w: ActiveWorkout, exId: string): ActiveWorkout {
  const i = w.exercises.findIndex((ex) => ex.id === exId);
  const next = w.exercises[i + 1];
  if (i < 0 || !next) return w;
  const cur = w.exercises[i];
  const exercises = [...w.exercises];
  if (cur.supersetGroupId && cur.supersetGroupId === next.supersetGroupId) {
    // Separar: lo que queda por debajo pasa a un grupo nuevo (normalize disuelve si queda solo).
    const group = cur.supersetGroupId;
    const fresh = uid();
    for (let j = i + 1; j < exercises.length; j++) {
      if (exercises[j].supersetGroupId === group) {
        exercises[j] = { ...exercises[j], supersetGroupId: fresh };
      }
    }
  } else {
    // Enlazar: fusiona los dos grupos completos (permite superseries de 3 o más).
    const group = cur.supersetGroupId ?? next.supersetGroupId ?? uid();
    const absorbed = new Set([cur.supersetGroupId, next.supersetGroupId].filter(Boolean));
    for (let j = 0; j < exercises.length; j++) {
      const ex = exercises[j];
      if (j === i || j === i + 1 || (ex.supersetGroupId && absorbed.has(ex.supersetGroupId))) {
        exercises[j] = { ...ex, supersetGroupId: group };
      }
    }
  }
  return { ...w, exercises: normalizeSupersets(exercises) };
}

export function substituteExercise(
  w: ActiveWorkout,
  exId: string,
  ex: CatalogExercise,
): ActiveWorkout {
  return mapEx(w, exId, (old) => ({
    ...old,
    exerciseId: ex.id,
    name: exerciseDisplayName(ex),
    imageUrl: ex.imageUrls[0] ?? null,
    previous: [],
    records: null,
    history: "pending",
  }));
}

export function setNote(w: ActiveWorkout, exId: string, note: string): ActiveWorkout {
  return mapEx(w, exId, (ex) => ({ ...ex, note }));
}

export function setRestSeconds(w: ActiveWorkout, exId: string, seconds: number): ActiveWorkout {
  const rest = Math.max(15, Math.min(600, seconds));
  return mapEx(w, exId, (ex) => ({ ...ex, restSeconds: rest }));
}

export function patchSet(
  w: ActiveWorkout,
  exId: string,
  setId: string,
  patch: Partial<Pick<WorkoutSet, "weight" | "reps" | "rpe">>,
): ActiveWorkout {
  return mapSet(w, exId, setId, (s) => ({ ...s, ...patch }));
}

export function cycleSetType(w: ActiveWorkout, exId: string, setId: string): ActiveWorkout {
  return mapSet(w, exId, setId, (s) => ({
    ...s,
    type: SET_TYPE_CYCLE[(SET_TYPE_CYCLE.indexOf(s.type) + 1) % SET_TYPE_CYCLE.length],
  }));
}

export function addSet(w: ActiveWorkout, exId: string): ActiveWorkout {
  return mapEx(w, exId, (ex) => {
    const last = ex.sets[ex.sets.length - 1];
    const copy: Partial<WorkoutSet> = last
      ? {
          weight: last.weight,
          reps: last.reps,
          targetRepsMin: last.targetRepsMin,
          targetRepsMax: last.targetRepsMax,
          type: last.type === "calentamiento" ? "normal" : last.type,
        }
      : {};
    return { ...ex, sets: [...ex.sets, newSet(copy)] };
  });
}

export function deleteSet(w: ActiveWorkout, exId: string, setId: string): ActiveWorkout {
  return mapEx(w, exId, (ex) => ({ ...ex, sets: ex.sets.filter((s) => s.id !== setId) }));
}

/** Valores efectivos (escritos o sugeridos) para una serie. */
export function effectiveValues(
  ex: WorkoutExercise,
  index: number,
): { weight: string; reps: string } {
  const set = ex.sets[index];
  const prev = ex.previous[index];
  const weight =
    set.weight !== "" ? set.weight : prev?.weightKg != null ? String(prev.weightKg) : "";
  const target = set.targetRepsMax ?? set.targetRepsMin;
  const reps =
    set.reps !== ""
      ? set.reps
      : prev?.reps != null
        ? String(prev.reps)
        : target != null
          ? String(target)
          : "";
  return { weight, reps };
}

export function canComplete(ex: WorkoutExercise, index: number): boolean {
  const reps = parseNum(effectiveValues(ex, index).reps);
  return reps != null && reps > 0;
}

/**
 * En superserie se descansa al cerrar la ronda: solo el último ejercicio del grupo
 * dispara el descanso (con su tiempo). Fuera de superserie, el propio ejercicio.
 */
export function supersetRestHolder(
  exercises: WorkoutExercise[],
  ex: WorkoutExercise,
): WorkoutExercise | null {
  if (!ex.supersetGroupId) return ex;
  const members = exercises.filter((e) => e.supersetGroupId === ex.supersetGroupId);
  return members[members.length - 1]?.id === ex.id ? ex : null;
}

/** Marca/desmarca; al marcar rellena con los valores sugeridos si están vacíos. */
export function toggleDone(w: ActiveWorkout, exId: string, setId: string): ActiveWorkout {
  const ex = w.exercises.find((e) => e.id === exId);
  if (!ex) return w;
  const index = ex.sets.findIndex((s) => s.id === setId);
  if (index < 0) return w;
  const set = ex.sets[index];
  if (set.done) {
    return mapSet(w, exId, setId, (s) => ({ ...s, done: false }));
  }
  if (!canComplete(ex, index)) return w;
  const eff = effectiveValues(ex, index);
  const next = mapSet(w, exId, setId, (s) => ({
    ...s,
    weight: eff.weight,
    reps: eff.reps,
    done: true,
  }));
  if (set.type === "calentamiento") return next;
  const restAfter = supersetRestHolder(w.exercises, ex);
  if (!restAfter) return { ...next, rest: null };
  const ms = restAfter.restSeconds * 1000;
  return { ...next, rest: { endsAt: Date.now() + ms, total: ms } };
}

export function adjustRest(w: ActiveWorkout, deltaMs: number): ActiveWorkout {
  if (!w.rest) return w;
  const endsAt = w.rest.endsAt + deltaMs;
  if (endsAt <= Date.now()) return { ...w, rest: null };
  return { ...w, rest: { endsAt, total: Math.max(1000, w.rest.total + deltaMs) } };
}

export function skipRest(w: ActiveWorkout): ActiveWorkout {
  return w.rest ? { ...w, rest: null } : w;
}

export function previousFromHistory(history: ExerciseHistory): PreviousSet[] {
  const last = history.sessions[0];
  if (!last) return [];
  return [...last.sets]
    .sort((a, b) => a.setNumber - b.setNumber)
    .map((s) => ({ weightKg: s.weightKg, reps: s.reps }));
}

export function applyHistory(
  w: ActiveWorkout,
  exId: string,
  history: ExerciseHistory | null,
): ActiveWorkout {
  return mapEx(w, exId, (ex) => ({
    ...ex,
    history: "loaded",
    previous: history ? previousFromHistory(history) : [],
    records: history ? history.records : null,
  }));
}

export type WorkoutStats = { volumeKg: number; setsDone: number; setsTotal: number };

export function workoutStats(w: ActiveWorkout): WorkoutStats {
  let volumeKg = 0;
  let setsDone = 0;
  let setsTotal = 0;
  for (const ex of w.exercises) {
    for (const s of ex.sets) {
      setsTotal += 1;
      if (!s.done) continue;
      setsDone += 1;
      if (s.type === "calentamiento") continue;
      volumeKg += (parseNum(s.weight) ?? 0) * (parseNum(s.reps) ?? 0);
    }
  }
  return { volumeKg, setsDone, setsTotal };
}
