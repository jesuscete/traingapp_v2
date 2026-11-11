import { api } from "@/lib/api";
import type { CatalogExercise } from "@/lib/types";

const SESSION_KEY = "traingapp_catalog_v3";

let memory: CatalogExercise[] | null = null;
let inflight: Promise<CatalogExercise[]> | null = null;

function readSession(): CatalogExercise[] | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? (JSON.parse(raw) as CatalogExercise[]) : null;
  } catch {
    return null;
  }
}

function writeSession(list: CatalogExercise[]): void {
  try {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(list));
  } catch {
    // cuota o modo privado: la caché en memoria basta
  }
}

export function getCatalog(
  token: string,
  force = false,
): Promise<CatalogExercise[]> {
  if (!force) {
    if (memory) return Promise.resolve(memory);
    const stored = readSession();
    if (stored) {
      memory = stored;
      return Promise.resolve(stored);
    }
  }
  if (inflight) return inflight;
  inflight = api
    .listCatalogExercises(token)
    .then((list) => {
      memory = list;
      writeSession(list);
      return list;
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}

export function patchCachedFavorite(id: string, isFavorite: boolean): void {
  if (!memory) return;
  memory = memory.map((ex) => (ex.id === id ? { ...ex, isFavorite } : ex));
  writeSession(memory);
}

/** Inserta o reemplaza un ejercicio (p. ej. uno propio recién creado). */
export function upsertCachedExercise(exercise: CatalogExercise): void {
  if (!memory) {
    invalidateCatalog();
    return;
  }
  memory = memory.some((ex) => ex.id === exercise.id)
    ? memory.map((ex) => (ex.id === exercise.id ? exercise : ex))
    : [...memory, exercise];
  writeSession(memory);
}

export function removeCachedExercise(id: string): void {
  if (!memory) {
    invalidateCatalog();
    return;
  }
  memory = memory.filter((ex) => ex.id !== id);
  writeSession(memory);
}

/** Descarta la caché: la próxima lectura vuelve a pedir el catálogo. */
export function invalidateCatalog(): void {
  memory = null;
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // sin sessionStorage: solo había memoria
  }
}

export function peekCatalog(): CatalogExercise[] | null {
  return memory;
}
