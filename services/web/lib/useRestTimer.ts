"use client";

import { useEffect, useRef, useState } from "react";

import { beep, vibrate } from "@/lib/alert";
import type { RestState } from "@/lib/workout/types";

/**
 * Cuenta atrás basada en timestamps: el resto se calcula con Date.now(),
 * así es correcto tras bloquear la pantalla. Devuelve ms restantes (o null).
 */
export function useRestTimer(rest: RestState | null, onExpire: () => void): number | null {
  const [now, setNow] = useState(() => Date.now());
  const expireRef = useRef(onExpire);
  useEffect(() => {
    expireRef.current = onExpire;
  }, [onExpire]);

  const endsAt = rest?.endsAt ?? null;

  useEffect(() => {
    if (endsAt === null) return;
    setNow(Date.now());
    const tick = () => {
      const t = Date.now();
      setNow(t);
      if (t >= endsAt) {
        window.clearInterval(id);
        // solo avisa si no ha pasado mucho (si no, la app estaba cerrada)
        if (t - endsAt < 5000) {
          beep();
          vibrate([300, 120, 300]);
        }
        expireRef.current();
      }
    };
    const id = window.setInterval(tick, 250);
    const onVisible = () => {
      if (document.visibilityState === "visible") tick();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [endsAt]);

  if (endsAt === null) return null;
  return Math.max(0, endsAt - now);
}

/** Segundos transcurridos desde `startedAt` (basado en timestamp). */
export function useElapsed(startedAt: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (startedAt === null) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    const onVisible = () => setNow(Date.now());
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [startedAt]);
  return startedAt === null ? 0 : Math.max(0, Math.floor((now - startedAt) / 1000));
}
