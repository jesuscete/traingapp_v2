import type { ActiveWorkout, PendingWorkout } from "@/lib/workout/types";

export const ACTIVE_KEY = "traingapp_active_workout_v1";
export const PENDING_KEY = "traingapp_pending_workouts_v1";

function read<T>(key: string): T | null {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown): void {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // almacenamiento no disponible
  }
}

export function loadActiveWorkout(): ActiveWorkout | null {
  const w = read<ActiveWorkout>(ACTIVE_KEY);
  return w && w.version === 1 && Array.isArray(w.exercises) ? w : null;
}

export function saveActiveWorkout(w: ActiveWorkout | null): void {
  write(ACTIVE_KEY, w);
}

export function loadPending(): PendingWorkout[] {
  const list = read<PendingWorkout[]>(PENDING_KEY);
  return Array.isArray(list) ? list : [];
}

export function savePending(list: PendingWorkout[]): void {
  write(PENDING_KEY, list.length > 0 ? list : null);
}

export function enqueuePending(item: PendingWorkout): void {
  savePending([...loadPending().filter((p) => p.clientId !== item.clientId), item]);
}

export function removePending(clientId: string): void {
  savePending(loadPending().filter((p) => p.clientId !== clientId));
}

/** Entrenos que el servidor rechazó de forma definitiva: se conservan para no perder datos. */
export const FAILED_KEY = "traingapp_failed_workouts_v1";
const MAX_FAILED = 20;

export function archiveFailed(item: PendingWorkout, error: string): void {
  const list = read<(PendingWorkout & { error: string })[]>(FAILED_KEY) ?? [];
  write(FAILED_KEY, [...list, { ...item, error }].slice(-MAX_FAILED));
}
