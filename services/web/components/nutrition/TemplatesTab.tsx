"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import { errMsg, kcal } from "@/lib/nutrition";
import type { MealName, MealTemplate } from "@/lib/types";
import { Trash2 } from "lucide-react";

type Props = { token: string; day: string; meal: MealName; onApplied: () => void };

export function TemplatesTab({ token, day, meal, onApplied }: Props) {
  const [templates, setTemplates] = useState<MealTemplate[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setTemplates(await api.listMealTemplates(token));
    } catch (err) {
      setError(errMsg(err, "No se pudieron cargar tus platos"));
      setTemplates([]);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function apply(t: MealTemplate) {
    setBusyId(t.id);
    setError(null);
    try {
      await api.applyMealTemplate(token, t.id, { eatenOn: day, meal });
      onApplied();
    } catch (err) {
      setError(errMsg(err, "No se pudo aplicar el plato"));
      setBusyId(null);
    }
  }

  async function remove(t: MealTemplate) {
    if (!window.confirm(`¿Borrar el plato «${t.name}»?`)) return;
    setBusyId(t.id);
    try {
      await api.deleteMealTemplate(token, t.id);
      await load();
    } catch (err) {
      setError(errMsg(err, "No se pudo borrar"));
    } finally {
      setBusyId(null);
    }
  }

  if (templates === null) return <Skeleton height={120} />;

  return (
    <div className="nu-form">
      {templates.length === 0 && (
        <p className="muted">
          Aún no tienes platos. Guarda una comida con «Guardar como plato» en su sección y podrás repetirla con un
          toque.
        </p>
      )}
      <ul className="nu-list">
        {templates.map((t) => (
          <li key={t.id} className="nu-tpl">
            <button
              type="button"
              className="nu-food-row"
              disabled={busyId !== null}
              onClick={() => apply(t)}
            >
              <span className="nu-food-main">
                <strong>{t.name}</strong>
                <span className="muted">
                  {t.items.length} {t.items.length === 1 ? "alimento" : "alimentos"} · {kcal(t.kcal)} kcal
                </span>
              </span>
              <span className="nu-add-tag">{busyId === t.id ? "…" : "Añadir"}</span>
            </button>
            <button
              type="button"
              className="secondary nu-icon-btn"
              aria-label={`Borrar plato ${t.name}`}
              disabled={busyId !== null}
              onClick={() => remove(t)}
            >
              <Trash2 size={16} strokeWidth={1.75} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      {error && <p className="error">{error}</p>}
    </div>
  );
}
