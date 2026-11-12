"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import { CreateExerciseSheet } from "@/components/gym/CreateExerciseSheet";
import { ExerciseThumb } from "@/components/gym/ExerciseThumb";
import { FavoriteButton } from "@/components/gym/FavoriteButton";
import {
  EMPTY_FILTERS,
  distinctValues,
  exerciseDisplayName,
  filterExercises,
  indexExercises,
  type ExerciseFilters,
} from "@/lib/exerciseSearch";
import { translateMuscleGroup } from "@/lib/labels";
import { useCatalog } from "@/lib/useCatalog";
import type { CatalogExercise } from "@/lib/types";
import { Star } from "lucide-react";

const PAGE_SIZE = 40;

const MUSCLE_ORDER = [
  "chest",
  "back",
  "shoulders",
  "biceps",
  "triceps",
  "forearms",
  "core",
  "quadriceps",
  "hamstrings",
  "glutes",
  "calves",
  "neck",
];

type Props = {
  token: string | null;
  /** Si se pasa, tocar una fila llama a esto (selector); si no, enlaza al detalle. */
  onPick?: (exercise: CatalogExercise) => void;
  autoFocus?: boolean;
  selectedId?: string | null;
};

export function ExerciseLibrary({ token, onPick, autoFocus, selectedId }: Props) {
  const { catalog, loading, error, retry, toggleFavorite, addExercise } = useCatalog(token);
  const [creating, setCreating] = useState(false);
  const [filters, setFilters] = useState<ExerciseFilters>(EMPTY_FILTERS);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [limit, setLimit] = useState(PAGE_SIZE);
  const sentinel = useRef<HTMLDivElement | null>(null);

  const index = useMemo(() => indexExercises(catalog), [catalog]);
  const equipments = useMemo(() => distinctValues(index, (i) => i.equipment), [index]);
  const categories = useMemo(() => distinctValues(index, (i) => i.category), [index]);
  const muscles = useMemo(() => {
    const present = new Set(index.flatMap((i) => i.primary));
    return MUSCLE_ORDER.filter((m) => present.has(m));
  }, [index]);
  const results = useMemo(() => filterExercises(index, filters), [index, filters]);

  useEffect(() => {
    setLimit(PAGE_SIZE);
  }, [filters]);

  const hasMore = limit < results.length;
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !hasMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) setLimit((n) => n + PAGE_SIZE);
      },
      { rootMargin: "400px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [hasMore, limit]);

  function patch(next: Partial<ExerciseFilters>) {
    setFilters((f) => ({ ...f, ...next }));
  }

  const activeFilters =
    Number(filters.muscle !== null) +
    Number(filters.equipment !== null) +
    Number(filters.category !== null);

  return (
    <div className="ex-lib">
      <div className="ex-lib-controls">
        <input
          className="ex-search"
          type="search"
          placeholder="Buscar ejercicio (es / en)"
          value={filters.query}
          autoFocus={autoFocus}
          autoComplete="off"
          onChange={(e) => patch({ query: e.target.value })}
          aria-label="Buscar ejercicio"
        />
        <div className="ex-chips" role="group" aria-label="Filtros">
          <button
            type="button"
            className={`ex-chip${filters.favoritesOnly ? " on" : ""}`}
            aria-pressed={filters.favoritesOnly}
            onClick={() => patch({ favoritesOnly: !filters.favoritesOnly })}
          >
            <Star size={14} strokeWidth={1.75} aria-hidden="true" /> Favoritos
          </button>
          <button
            type="button"
            className={`ex-chip${filters.customOnly ? " on" : ""}`}
            aria-pressed={filters.customOnly}
            onClick={() => patch({ customOnly: !filters.customOnly })}
          >
            Propios
          </button>
          {muscles.map((m) => (
            <button
              key={m}
              type="button"
              className={`ex-chip${filters.muscle === m ? " on" : ""}`}
              aria-pressed={filters.muscle === m}
              onClick={() => patch({ muscle: filters.muscle === m ? null : m })}
            >
              {translateMuscleGroup(m)}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="ex-more-filters"
          aria-expanded={showAdvanced}
          onClick={() => setShowAdvanced((v) => !v)}
        >
          Equipo y categoría{activeFilters > 0 ? ` (${activeFilters})` : ""}
          {showAdvanced ? " ▴" : " ▾"}
        </button>
        {showAdvanced && (
          <div className="ex-adv">
            <label>
              <span className="muted">Equipo</span>
              <select
                value={filters.equipment ?? ""}
                onChange={(e) => patch({ equipment: e.target.value || null })}
              >
                <option value="">Todos</option>
                {equipments.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="muted">Categoría</span>
              <select
                value={filters.category ?? ""}
                onChange={(e) => patch({ category: e.target.value || null })}
              >
                <option value="">Todas</option>
                {categories.map((v) => (
                  <option key={v} value={v}>
                    {v}
                  </option>
                ))}
              </select>
            </label>
          </div>
        )}
      </div>

      {loading && catalog.length === 0 && (
        <div className="stack">
          <Skeleton height={56} />
          <Skeleton height={56} />
          <Skeleton height={56} />
        </div>
      )}
      {error && (
        <p className="error">
          {error}{" "}
          <button type="button" className="link" onClick={retry}>
            Reintentar
          </button>
        </p>
      )}
      {!loading && !error && results.length === 0 && (
        <p className="muted ex-empty">
          {filters.favoritesOnly && catalog.length > 0
            ? "Aún no tienes favoritos con estos filtros."
            : filters.customOnly && catalog.length > 0
              ? "Aún no has creado ejercicios propios."
              : "No hay ejercicios que coincidan."}
        </p>
      )}
      {!loading && !error && results.length === 0 && token && (
        <button type="button" className="secondary ce-create-btn" onClick={() => setCreating(true)}>
          {filters.query.trim() ? `+ Crear «${filters.query.trim()}»` : "+ Crear ejercicio"}
        </button>
      )}

      {results.length > 0 && (
        <div className="ex-toolbar">
          <p className="muted ex-count">{results.length} ejercicios</p>
          {token && (
            <button type="button" className="secondary ce-create-btn" onClick={() => setCreating(true)}>
              + Crear ejercicio
            </button>
          )}
        </div>
      )}
      <ul className="ex-list">
        {results.slice(0, limit).map((ex) => (
          <ExerciseRow
            key={ex.id}
            ex={ex}
            onPick={onPick}
            selected={selectedId === ex.id}
            onToggleFavorite={() => void toggleFavorite(ex.id)}
          />
        ))}
      </ul>
      {hasMore && <div ref={sentinel} className="ex-sentinel" aria-hidden="true" />}
      {creating && token && (
        <CreateExerciseSheet
          token={token}
          initialName={filters.query.trim()}
          onClose={() => setCreating(false)}
          onCreated={(created) => {
            addExercise(created);
            setCreating(false);
            if (onPick) onPick(created);
          }}
        />
      )}
    </div>
  );
}

function ExerciseRow({
  ex,
  onPick,
  selected,
  onToggleFavorite,
}: {
  ex: CatalogExercise;
  selected?: boolean;
  onPick?: (exercise: CatalogExercise) => void;
  onToggleFavorite: () => void;
}) {
  const primary = Object.entries(ex.muscleMap)
    .filter(([, v]) => v >= 0.5)
    .sort((a, b) => b[1] - a[1])
    .map(([k]) => translateMuscleGroup(k))
    .slice(0, 2)
    .join(", ");
  const meta = [primary, ex.details?.equipment].filter(Boolean).join(" · ");
  const body = (
    <>
      <ExerciseThumb src={ex.imageUrls[0]} />
      <span className="ex-row-text">
        <span className="ex-row-name">
          {exerciseDisplayName(ex)}
          {ex.isCustom && <span className="ex-badge">Propio</span>}
        </span>
        <span className="ex-row-meta">{meta || "—"}</span>
      </span>
    </>
  );
  return (
    <li className={`ex-row${selected ? " selected" : ""}`}>
      {onPick ? (
        <button type="button" className="ex-row-main" onClick={() => onPick(ex)}>
          {body}
        </button>
      ) : (
        <Link className="ex-row-main" href={`/ejercicios/${ex.id}`}>
          {body}
        </Link>
      )}
      <FavoriteButton active={ex.isFavorite} onToggle={onToggleFavorite} />
    </li>
  );
}
