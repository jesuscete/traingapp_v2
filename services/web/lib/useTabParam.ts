"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback } from "react";

/** Sincroniza el segmento activo con `?tab=`. El componente que lo use debe ir dentro de <Suspense>. */
export function useTabParam<T extends string>(ids: readonly T[], fallback: T): [T, (id: T) => void] {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const raw = params.get("tab");
  const value = ids.find((id) => id === raw) ?? fallback;
  const setValue = useCallback(
    (id: T) => {
      const next = new URLSearchParams(params.toString());
      next.set("tab", id);
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, pathname, router],
  );
  return [value, setValue];
}
