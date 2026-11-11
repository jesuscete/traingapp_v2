import { ApiError, api } from "@/lib/api";
import {
  archiveFailed,
  enqueuePending,
  loadPending,
  removePending,
} from "@/lib/workout/storage";
import type { GymSession, GymSessionIn } from "@/lib/types";

export type SubmitOutcome =
  | { status: "saved"; session: GymSession }
  | { status: "queued"; reason: string };

const RETRYABLE_4XX = new Set([401, 408, 429]);

/** Red caída o 5xx / 401 / 408 / 429: merece reintento. */
function isRetryable(err: unknown): boolean {
  if (err instanceof ApiError) {
    return err.status >= 500 || RETRYABLE_4XX.has(err.status);
  }
  return true; // fallo de red (TypeError de fetch) u otro no HTTP
}

/** Envía el entreno; si falla de forma reintentable lo deja en cola. Un 4xx definitivo se propaga. */
export async function submitWorkout(
  token: string,
  clientId: string,
  payload: GymSessionIn,
): Promise<SubmitOutcome> {
  const body: GymSessionIn = { ...payload, clientId };
  try {
    const session = await api.createGymSession(token, body);
    return { status: "saved", session };
  } catch (err) {
    if (isRetryable(err)) {
      enqueuePending({ clientId, savedAt: Date.now(), payload: body });
      return {
        status: "queued",
        reason: err instanceof Error ? err.message : "Sin conexión",
      };
    }
    throw err;
  }
}

let flushing = false;

export type FlushResult = { sent: number; rejected: string[] };

/** Reintenta la cola. Los 4xx definitivos se descartan y se devuelven como errores. */
export async function flushPending(token: string): Promise<FlushResult> {
  const result: FlushResult = { sent: 0, rejected: [] };
  if (flushing) return result;
  flushing = true;
  try {
    for (const item of loadPending()) {
      try {
        await api.createGymSession(token, { ...item.payload, clientId: item.clientId });
        removePending(item.clientId);
        result.sent += 1;
      } catch (err) {
        if (isRetryable(err)) {
          if (!(err instanceof ApiError)) break; // sin red: parar
          continue;
        }
        const message = err instanceof Error ? err.message : "rechazado";
        archiveFailed(item, message);
        removePending(item.clientId);
        result.rejected.push(`${item.payload.rawText}: ${message}`);
      }
    }
  } finally {
    flushing = false;
  }
  return result;
}
