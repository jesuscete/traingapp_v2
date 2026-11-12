"use client";

import { useEffect, useState } from "react";

import { AlternativesList } from "@/components/gym/AlternativesList";
import { ExerciseLibrary } from "@/components/gym/ExerciseLibrary";
import { exerciseDisplayName } from "@/lib/exerciseSearch";
import type { CatalogExercise } from "@/lib/types";
import { X } from "lucide-react";

type Props = {
  token: string | null;
  title: string;
  /** Una sola selección (sustituir) o varias (añadir). */
  multiple: boolean;
  /** Si se pasa, muestra alternativas recomendadas para ese ejercicio del catálogo. */
  alternativesFor?: string | null;
  onClose: () => void;
  onConfirm: (exercises: CatalogExercise[]) => void;
};

export function AddExerciseSheet({ token, title, multiple, alternativesFor, onClose, onConfirm }: Props) {
  const [selected, setSelected] = useState<CatalogExercise[]>([]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  function pick(ex: CatalogExercise) {
    if (!multiple) {
      onConfirm([ex]);
      return;
    }
    setSelected((list) =>
      list.some((item) => item.id === ex.id)
        ? list.filter((item) => item.id !== ex.id)
        : [...list, ex],
    );
  }

  return (
    <div className="sheet-backdrop" role="presentation" onClick={onClose}>
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-head">
          <h3>{title}</h3>
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Cerrar">
            <X size={18} strokeWidth={1.75} aria-hidden="true" />
          </button>
        </div>
        <div className="sheet-body">
          {alternativesFor && (
            <AlternativesList token={token} exerciseId={alternativesFor} onPick={pick} />
          )}
          <ExerciseLibrary token={token} onPick={pick} />
        </div>
        {multiple && (
          <div className="sheet-foot">
            {selected.length > 0 && (
              <p className="muted sheet-selected">
                {selected.map((ex) => exerciseDisplayName(ex)).join(", ")}
              </p>
            )}
            <button
              type="button"
              className="wk-primary"
              disabled={selected.length === 0}
              onClick={() => onConfirm(selected)}
            >
              {selected.length === 0
                ? "Toca ejercicios para seleccionarlos"
                : `Añadir ${selected.length} ejercicio${selected.length > 1 ? "s" : ""}`}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
