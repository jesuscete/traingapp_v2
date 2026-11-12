"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Plus } from "lucide-react";

import { BottomNav } from "@/components/BottomNav";
import { AddFoodSheet } from "@/components/nutrition/AddFoodSheet";
import { DaySummary } from "@/components/nutrition/DaySummary";
import { EditEntrySheet, TemplateNameSheet } from "@/components/nutrition/EntrySheets";
import { GoalSheet } from "@/components/nutrition/GoalSheet";
import { MealSection } from "@/components/nutrition/MealSection";
import { WeightCard } from "@/components/nutrition/WeightCard";
import { Button } from "@/components/ui/Button";
import { Fab } from "@/components/ui/Fab";
import { Segmented, type SegmentItem } from "@/components/ui/Segmented";
import { StatTile } from "@/components/ui/StatTile";
import { Skeleton } from "@/components/ui/Skeleton";
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
import { useTabParam } from "@/lib/useTabParam";
import { useToken } from "@/lib/useToken";
import type { MealEntry, MealName, NutritionDay, NutritionWeek } from "@/lib/types";

const TABS = ["dia", "semana", "peso"] as const;
type Tab = (typeof TABS)[number];

const ITEMS: SegmentItem<Tab>[] = [
  { id: "dia", label: "Día" },
  { id: "semana", label: "Semana" },
  { id: "peso", label: "Peso y objetivo" },
];

function ComidasInner() {
  const token = useToken();
  const [tab, setTab] = useTabParam<Tab>(TABS, "dia");
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
    if (window.location.hash === "#objetivo") {
      setGoalOpen(true);
      setTab("peso");
    }
    // solo al montar: mapea /comidas#objetivo a la pestaña de peso y abre la hoja
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

      <Segmented items={ITEMS} value={tab} onChange={setTab} label="Secciones de comidas" />

      <span id="objetivo" />

      {tab !== "peso" && (
      <div className="nu-daynav">
        <button type="button" className="secondary" aria-label="Día anterior" onClick={() => setDay(shiftDay(day, -1))}>
          <ChevronLeft size={20} strokeWidth={1.75} aria-hidden="true" />
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
          <ChevronRight size={20} strokeWidth={1.75} aria-hidden="true" />
        </button>
        {!isToday && (
          <Button variant="text" onClick={() => setDay(todayISO())}>
            Hoy
          </Button>
        )}
      </div>

      )}

      {error && <p className="error">{error}</p>}
      {loading && !data && <Skeleton height={220} />}

      {data && tab === "dia" && (
        <div className="nu-dia">
          <div className="nu-dia-side">
          <DaySummary data={data} />

          {week && week.days.length > 0 && (
            <p className="muted nu-weekline">
              Media 7 días: {kcal(week.averageKcal)} kcal
              {week.averageTargetKcal !== null ? ` (objetivo medio ${kcal(week.averageTargetKcal)})` : ""}
            </p>
          )}
          </div>

          <div className="nu-dia-meals">
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
          </div>
        </div>
      )}

      {data && tab === "semana" && week && (
        <section className="energy-card">
          <h3>Últimos 7 días</h3>
          <div className="ui-stat-row">
            <StatTile value={kcal(week.averageKcal)} label="kcal de media" />
            {week.averageTargetKcal !== null && <StatTile value={kcal(week.averageTargetKcal)} label="objetivo medio" />}
          </div>
          <ul className="nu-week-list">
            {week.days.map((d) => (
              <li key={d.day}>
                <button type="button" className="nu-daylabel" onClick={() => { setDay(d.day); setTab("dia"); }}>
                  {dayLabel(d.day)}
                </button>
                <span> · {kcal(d.kcal)} kcal{d.targetKcal !== null ? ` / ${kcal(d.targetKcal)}` : ""} · {Math.round(d.proteinG)} g prot.</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {tab === "peso" && token && (
        <>
          <div id="peso">
            <WeightCard token={token} day={day} onChanged={load} />
          </div>
          <section className="energy-card">
            <h3>Objetivo nutricional</h3>
            <p className="subtitle">Calorías, proteína y peso objetivo.</p>
            <button type="button" className="secondary nu-goal-btn" onClick={() => setGoalOpen(true)}>
              Editar objetivo
            </button>
          </section>
        </>
      )}

      {tab === "dia" && !adding && (
        <Fab label="Añadir" icon={<Plus size={24} strokeWidth={1.75} aria-hidden="true" />} onClick={() => setAdding(defaultMealForNow())} />
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

export default function Comidas() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <ComidasInner />
    </Suspense>
  );
}
