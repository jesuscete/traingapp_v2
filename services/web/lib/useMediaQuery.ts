"use client";

import { useSyncExternalStore } from "react";

/** true cuando la media query coincide (false en servidor y primer render). */
export function useMediaQuery(query: string): boolean {
  return useSyncExternalStore(
    (cb) => {
      const mq = window.matchMedia(query);
      mq.addEventListener("change", cb);
      return () => mq.removeEventListener("change", cb);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

export const useIsExpanded = (): boolean => useMediaQuery("(min-width: 1024px)");
