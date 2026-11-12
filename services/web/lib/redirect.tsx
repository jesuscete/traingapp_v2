"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** Página mínima que reenvía a la nueva ubicación (conserva enlaces antiguos). */
export function RedirectTo({ to }: { to: string }) {
  const router = useRouter();
  useEffect(() => {
    router.replace(to);
  }, [router, to]);
  return <p className="muted">Redirigiendo...</p>;
}
