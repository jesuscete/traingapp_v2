"use client";

import { ChevronRight } from "lucide-react";

import { StatTile } from "@/components/ui/StatTile";
import { dayStatus, type DayStatus } from "@/lib/macros";
import { dayLabel, kcal, todayISO } from "@/lib/nutrition";
import type { NutritionWeek } from "@/lib/types";

const STATUS_LABEL: Record<DayStatus, string> = {
  empty: "Sin registrar",
  progress: "En curso",
  ok: "En objetivo",
  low: "Por debajo",
  high: "Por encima",
};

type Day = NutritionWeek["days"][number];

function DayRow({ d, onOpen }: { d: Day; onOpen: () => void }) {
  const isToday = d.day === todayISO();
  const status = dayStatus(d.kcal, d.targetKcal, isToday);
  // La barra llega al 100 % en 1,25× el objetivo para que el exceso se vea.
  const scale = d.targetKcal ? d.targetKcal * 1.25 : Math.max(d.kcal, 1);
  const fill = Math.min(100, (d.kcal / scale) * 100);
  const mark = d.targetKcal ? (d.targetKcal / scale) * 100 : null;
  const macroKcal = d.proteinG * 4 + d.carbsG * 4 + d.fatG * 9;
  const share = (k: number) => (macroKcal > 0 ? (k / macroKcal) * 100 : 0);

  return (
    <li>
      <button type="button" className={`nw-day ${status}`} onClick={onOpen}>
        <span className="nw-day-head">
          <strong>{dayLabel(d.day)}</strong>
          <span className={`nw-chip ${status}`}>{STATUS_LABEL[status]}</span>
        </span>
        {status === "empty" ? (
          <span className="nw-empty">Toca para añadir comidas</span>
        ) : (
          <>
            <span className="nw-kcal">
              <b>{kcal(d.kcal)}</b>
              {d.targetKcal !== null && <span className="muted"> / {kcal(d.targetKcal)} kcal</span>}
            </span>
            <span className="nw-bar" aria-hidden="true">
              <span className="nw-bar-fill" style={{ width: `${fill}%` }} />
              {mark !== null && <span className="nw-bar-mark" style={{ left: `${mark}%` }} />}
            </span>
            <span className="nw-macros">
              <span className="nw-mix" aria-hidden="true">
                <span className="p" style={{ width: `${share(d.proteinG * 4)}%` }} />
                <span className="c" style={{ width: `${share(d.carbsG * 4)}%` }} />
                <span className="f" style={{ width: `${share(d.fatG * 9)}%` }} />
              </span>
              <span className="nw-macro-txt">
                <i className="p" /> P {Math.round(d.proteinG)}
                {d.targetProteinG ? `/${Math.round(d.targetProteinG)}` : ""} g
                <i className="c" /> H {Math.round(d.carbsG)} g
                <i className="f" /> G {Math.round(d.fatG)} g
              </span>
            </span>
          </>
        )}
        <ChevronRight className="nw-go" size={18} strokeWidth={1.75} aria-hidden="true" />
      </button>
    </li>
  );
}

export function WeekView({ week, onOpenDay }: { week: NutritionWeek; onOpenDay: (day: string) => void }) {
  const days = [...week.days].reverse();
  const logged = week.days.filter((d) => d.kcal > 0);
  const avgProtein = logged.length ? logged.reduce((a, d) => a + d.proteinG, 0) / logged.length : 0;
  const onTarget = logged.filter((d) => dayStatus(d.kcal, d.targetKcal, false) === "ok").length;

  return (
    <section className="energy-card nw">
      <h3>Últimos 7 días</h3>
      <div className="ui-stat-row">
        <StatTile
          value={logged.length ? kcal(week.averageKcal) : "—"}
          label={week.averageTargetKcal !== null ? `kcal/día · obj. ${kcal(week.averageTargetKcal)}` : "kcal/día"}
        />
        <StatTile value={logged.length ? `${Math.round(avgProtein)} g` : "—"} label="proteína/día" />
        <StatTile value={`${onTarget}/${logged.length}`} label="días en objetivo" />
      </div>
      <ul className="nw-list">
        {days.map((d) => (
          <DayRow key={d.day} d={d} onOpen={() => onOpenDay(d.day)} />
        ))}
      </ul>
    </section>
  );
}
