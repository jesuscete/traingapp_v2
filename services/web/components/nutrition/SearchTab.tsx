"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { errMsg, g1, kcal } from "@/lib/nutrition";
import type { Food } from "@/lib/types";

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

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const timer = window.setTimeout(() => {
      api
        .searchFoods(token, q)
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
  }, [query, token]);

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
                {tag && <span className={`nu-badge nu-src-${food.source}`}>{tag}</span>}
              </button>
            </li>
          );
        })}
      </ul>
      {searched && !loading && results.length === 0 && (
        <p className="muted">Sin resultados para «{query.trim()}».</p>
      )}
      <button type="button" className="secondary nu-add-link" onClick={() => onCreate(query.trim())}>
        + Crear alimento (etiqueta)
      </button>
    </div>
  );
}
