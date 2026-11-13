"use client";

import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { normalizeText } from "@/lib/exerciseSearch";
import { errMsg, g1, kcal } from "@/lib/nutrition";
import type { Food, FoodFacets } from "@/lib/types";

type Props = {
  token: string;
  onPick: (food: Food) => void;
  onCreate: (name: string) => void;
};

function sourceTag(food: Food): string | null {
  if (food.isCustom || food.source === "custom") return "Tuyo";
  if (food.source === "usda") return "USDA";
  if (food.source === "off") return "OFF";
  return null;
}

export function SearchTab({ token, onPick, onCreate }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Food[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);
  const [store, setStore] = useState("");
  const [brand, setBrand] = useState("");
  const [facets, setFacets] = useState<FoodFacets>({ stores: [], brands: [] });

  useEffect(() => {
    let cancelled = false;
    api
      .getFoodFacets(token, store || undefined)
      .then((f) => {
        if (!cancelled) setFacets(f);
      })
      .catch(() => undefined); // sin filtros disponibles: la búsqueda sigue funcionando
    return () => {
      cancelled = true;
    };
  }, [token, store]);

  const [brandOpen, setBrandOpen] = useState(false);
  // Solo filtra por marca cuando coincide con una opción (no a mitad de escribirla).
  const brandKey = normalizeText(brand).replace(/[\s\-.'&]/g, "");
  const brandFilter =
    facets.brands.find((b) => normalizeText(b).replace(/[\s\-.'&]/g, "") === brandKey) ?? "";
  // Sugerencias mientras escribes: primero las que empiezan por el texto, luego las que lo contienen.
  const brandSuggestions = useMemo(() => {
    const q = normalizeText(brand);
    if (!q || brandFilter) return [];
    const starts = facets.brands.filter((b) => normalizeText(b).startsWith(q));
    const contains = facets.brands.filter((b) => !normalizeText(b).startsWith(q) && normalizeText(b).includes(q));
    return [...starts, ...contains].slice(0, 8);
  }, [brand, brandFilter, facets.brands]);
  const filtered = Boolean(store || brandFilter);

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2 && !filtered) {
      setResults([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api
        .searchFoods(token, q, { store: store || undefined, brand: brandFilter || undefined })
        .then((list) => {
          if (cancelled) return;
          setResults(list);
          setError(null);
          setSearched(true);
        })
        .catch((err: unknown) => {
          if (!cancelled) setError(errMsg(err, "No se pudo buscar"));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [query, token, store, brandFilter, filtered]);

  return (
    <div className="nu-search">
      <input
        type="search"
        className="nu-search-input"
        placeholder="Buscar alimento (ej.: pechuga de pollo)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        autoFocus
      />
      <div className="nu-filters">
        <label className="nu-filter">
          <span>Súper</span>
          <select value={store} onChange={(e) => setStore(e.target.value)}>
            <option value="">Todos</option>
            {facets.stores.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="nu-filter nu-brand">
          <span>Marca</span>
          <input
            type="search"
            placeholder="Todas"
            autoComplete="off"
            value={brand}
            onChange={(e) => {
              setBrand(e.target.value);
              setBrandOpen(true);
            }}
            onFocus={() => setBrandOpen(true)}
            onBlur={() => window.setTimeout(() => setBrandOpen(false), 150)}
          />
          {brandOpen && brandSuggestions.length > 0 && (
            <ul className="nu-suggest" role="listbox">
              {brandSuggestions.map((b) => (
                <li key={b}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => {
                      setBrand(b);
                      setBrandOpen(false);
                    }}
                  >
                    {b}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </label>
      </div>
      {loading && <p className="muted nu-pulse">Buscando…</p>}
      {error && <p className="error">{error}</p>}
      <ul className="nu-list">
        {results.map((food) => {
          const tag = sourceTag(food);
          return (
            <li key={food.id}>
              <button type="button" className="nu-food-row" onClick={() => onPick(food)}>
                <span className="nu-food-main">
                  <strong>{food.name}</strong>
                  <span className="muted">
                    {food.brand ? `${food.brand} · ` : ""}
                    {kcal(food.kcal100g)} kcal/100 g · P {g1(food.protein100g)} · H {g1(food.carbs100g)} · G{" "}
                    {g1(food.fat100g)}
                  </span>
                </span>
                {food.store ? (
                  <span className="nu-badge nu-store">{food.store}</span>
                ) : (
                  tag && <span className={`nu-badge nu-src-${food.source}`}>{tag}</span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {searched && !loading && results.length === 0 && (
        <p className="muted">
          Sin resultados{query.trim() ? ` para «${query.trim()}»` : ""}
          {filtered ? " con estos filtros" : ""}.
        </p>
      )}
      <button type="button" className="secondary nu-add-link" onClick={() => onCreate(query.trim())}>
        + Crear alimento (etiqueta)
      </button>
    </div>
  );
}
