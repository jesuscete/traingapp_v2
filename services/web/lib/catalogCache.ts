import { api } from "@/lib/api";
import type { CatalogExercise } from "@/lib/types";

const SESSION_KEY = "traingapp_catalog_v2";

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

export function peekCatalog(): CatalogExercise[] | null {
  return memory;
}
