"use client";

import { useCallback, useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { AddFoodSheet } from "@/components/nutrition/AddFoodSheet";
import { DaySummary } from "@/components/nutrition/DaySummary";
import { EditEntrySheet, TemplateNameSheet } from "@/components/nutrition/EntrySheets";
import { GoalSheet } from "@/components/nutrition/GoalSheet";
import { MealSection } from "@/components/nutrition/MealSection";
import { WeightCard } from "@/components/nutrition/WeightCard";
import { api } from "@/lib/api";
import {
  dayLabel,
  defaultMealForNow,
  errMsg,
  kcal,
  MEALS,
  shiftDay,
  todayISO,
} from "@/lib/nutrition";
import { useToken } from "@/lib/useToken";
import type { MealEntry, MealName, NutritionDay, NutritionWeek } from "@/lib/types";

export default function Comidas() {
  const token = useToken();
  const [day, setDay] = useState<string>(todayISO());
  const [data, setData] = useState<NutritionDay | null>(null);
  const [week, setWeek] = useState<NutritionWeek | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [adding, setAdding] = useState<MealName | null>(null);
  const [editing, setEditing] = useState<MealEntry | null>(null);
  const [templateFor, setTemplateFor] = useState<MealName | null>(null);
  const [goalOpen, setGoalOpen] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    try {
      const [d, w] = await Promise.all([api.getNutritionDay(token, day), api.getNutritionWeek(token, day)]);
      setData(d);
      setWeek(w);
      setError(null);
    } catch (err) {
      setError(errMsg(err, "No se pudo cargar el día"));
    } finally {
      setLoading(false);
    }
  }, [token, day]);

  useEffect(() => {
    if (window.location.hash === "#objetivo") setGoalOpen(true);
  }, []);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 2500);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function remove(entry: MealEntry) {
    if (!token) return;
    if (!window.confirm(`¿Borrar «${entry.name}» (${kcal(entry.kcal)} kcal)?`)) return;
    try {
      await api.deleteMealEntry(token, entry.id);
      await load();
    } catch (err) {
      setError(errMsg(err, "No se pudo borrar"));
    }
  }

  const isToday = day === todayISO();

  return (
    <main className="dashboard nu-page">
      <BottomNav />

      <section className="welcome nu-head" id="objetivo">
        <h2>Comidas</h2>
        <button type="button" className="secondary nu-goal-btn" onClick={() => setGoalOpen(true)}>
          Objetivo
        </button>
      </section>

      <div className="nu-daynav">
        <button type="button" className="secondary" aria-label="Día anterior" onClick={() => setDay(shiftDay(day, -1))}>
          ◀
        </button>
        <button
          type="button"
          className="nu-daylabel"
          disabled={isToday}
          onClick={() => setDay(todayISO())}
          aria-label="Ir a hoy"
        >
          {dayLabel(day)}
        </button>
        <button type="button" className="secondary" aria-label="Día siguiente" onClick={() => setDay(shiftDay(day, 1))}>
          ▶
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && !data && <p className="muted">Cargando...</p>}

      {data && (
        <>
          <DaySummary data={data} />

          {week && week.days.length > 0 && (
            <p className="muted nu-weekline">
              Media 7 días: {kcal(week.averageKcal)} kcal
              {week.averageTargetKcal !== null ? ` (objetivo medio ${kcal(week.averageTargetKcal)})` : ""}
            </p>
          )}

          <button
            type="button"
            className="wk-primary nu-main-add"
            onClick={() => setAdding(defaultMealForNow())}
          >
            + Añadir comida
          </button>

          {MEALS.map((m) => (
            <MealSection
              key={m.key}
              label={m.label}
              entries={data.meals[m.key] ?? []}
              onAdd={() => setAdding(m.key)}
              onEdit={setEditing}
              onDelete={remove}
              onSaveTemplate={() => setTemplateFor(m.key)}
            />
          ))}
        </>
      )}

      {token && (
        <div id="peso">
          <WeightCard token={token} day={day} onChanged={load} />
        </div>
      )}

      {toast && <p className="nu-toast ok">{toast}</p>}

      {token && adding && (
        <AddFoodSheet token={token} day={day} meal={adding} onClose={() => setAdding(null)} onChanged={load} />
      )}
      {token && editing && (
        <EditEntrySheet token={token} entry={editing} onClose={() => setEditing(null)} onChanged={load} />
      )}
      {token && data && templateFor && (
        <TemplateNameSheet
          token={token}
          entries={data.meals[templateFor] ?? []}
          defaultName={MEALS.find((m) => m.key === templateFor)?.label ?? "Plato"}
          onClose={() => setTemplateFor(null)}
          onSaved={() => setToast("Plato guardado")}
        />
      )}
      {token && goalOpen && <GoalSheet token={token} onClose={() => setGoalOpen(false)} onSaved={load} />}
    </main>
  );
}
