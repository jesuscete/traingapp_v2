"use client";

import { useCallback, useEffect, useState } from "react";

import { getCatalog, patchCachedFavorite, peekCatalog } from "@/lib/catalogCache";
import { api } from "@/lib/api";
import type { CatalogExercise } from "@/lib/types";

export function useCatalog(token: string | null) {
  const [catalog, setCatalog] = useState<CatalogExercise[]>(peekCatalog() ?? []);
  const [loading, setLoading] = useState(peekCatalog() === null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    getCatalog(token, attempt > 0)
      .then((list) => {
        if (!cancelled) setCatalog(list);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "No se pudo cargar el catálogo");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, attempt]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const toggleFavorite = useCallback(
    async (id: string) => {
      if (!token) return;
      const current = catalog.find((ex) => ex.id === id);
      if (!current) return;
      const next = !current.isFavorite;
      patchCachedFavorite(id, next);
      setCatalog((list) => list.map((ex) => (ex.id === id ? { ...ex, isFavorite: next } : ex)));
      try {
        await api.setExerciseFavorite(token, id, next);
      } catch {
        patchCachedFavorite(id, !next);
        setCatalog((list) =>
          list.map((ex) => (ex.id === id ? { ...ex, isFavorite: !next } : ex)),
        );
        setError("No se pudo actualizar el favorito");
      }
    },
    [token, catalog],
  );

  return { catalog, loading, error, retry, toggleFavorite };
}
