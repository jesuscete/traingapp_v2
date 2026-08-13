"use client";

import { useMemo, useRef, useState } from "react";

import { CATEGORY_LABELS } from "@/lib/labels";
import type { Discipline } from "@/lib/types";

function norm(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

type Props = {
  disciplines: Discipline[];
  value: string;
  onChange: (disciplineId: string) => void;
};

export function DisciplinePicker({ disciplines, value, onChange }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = disciplines.find((item) => item.id === value) ?? null;

  const filtered = useMemo(() => {
    const q = norm(query.trim());
    if (!q) return disciplines;
    return disciplines.filter((item) => {
      const haystack = norm(
        `${item.name} ${item.normalizedName} ${
          CATEGORY_LABELS[item.category] ?? item.category
        }`,
      );
      return haystack.includes(q);
    });
  }, [disciplines, query]);

  function handleBlur() {
    setTimeout(() => setOpen(false), 150);
  }

  return (
    <div className="discipline-picker" ref={containerRef}>
      <input
        type="text"
        placeholder={selected ? selected.name : "Buscar disciplina…"}
        value={open ? query : (selected?.name ?? "")}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          setQuery("");
          setOpen(true);
        }}
        onBlur={handleBlur}
        aria-label="Disciplina"
      />
      {open && (
        <ul className="discipline-picker-list">
          {filtered.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className={`discipline-picker-option${
                  item.id === value ? " selected" : ""
                }`}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  onChange(item.id);
                  setQuery("");
                  setOpen(false);
                }}
              >
                <span>{item.name}</span>
                <span className="discipline-picker-category">
                  {CATEGORY_LABELS[item.category] ?? item.category}
                </span>
              </button>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="discipline-picker-empty">Sin resultados</li>
          )}
        </ul>
      )}
    </div>
  );
}
