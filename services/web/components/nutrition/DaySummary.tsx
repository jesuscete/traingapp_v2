"use client";

import Link from "next/link";
import { useState } from "react";

import { g1, kcal } from "@/lib/nutrition";
import type { NutritionDay } from "@/lib/types";

const R = 52;
const CIRC = 2 * Math.PI * R;

function MacroBar({ label, value, target }: { label: string; value: number; target: number | null }) {
  const pct = target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const over = target !== null && target > 0 && value > target * 1.05;
  return (
    <div className="nu-macro">
      <div className="nu-macro-head">
        <span>{label}</span>
        <span className="muted">
          {Math.round(value)}
          {target !== null ? ` / ${Math.round(target)}` : ""} g
        </span>
      </div>
      <div className="nu-macro-track">
        <div className={`nu-macro-fill${over ? " over" : ""}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function DaySummary({ data }: { data: NutritionDay }) {
  const [open, setOpen] = useState(false);
  const { totals, target } = data;
  const consumed = totals.kcal;
  const goal = target?.targetKcal ?? null;
  const remaining = goal !== null ? goal - consumed : null;
  const ratio = goal ? Math.min(1, consumed / goal) : 0;
  const over = remaining !== null && remaining < 0;

  return (
    <section className="block nu-summary">
      <div className="nu-ring-row">
        <div className="nu-ring" role="img" aria-label={`${kcal(consumed)} kcal consumidas`}>
          <svg viewBox="0 0 120 120">
            <circle className="nu-ring-bg" cx="60" cy="60" r={R} />
            <circle
              className={`nu-ring-fg${over ? " over" : ""}`}
              cx="60"
              cy="60"
              r={R}
              strokeDasharray={`${ratio * CIRC} ${CIRC}`}
              transform="rotate(-90 60 60)"
            />
          </svg>
          <div className="nu-ring-text">
            <strong>{kcal(consumed)}</strong>
            <span className="muted">{goal !== null ? `de ${kcal(goal)} kcal` : "kcal"}</span>
          </div>
        </div>
        <div className="nu-remaining">
          {remaining !== null ? (
            <>
              <strong className={over ? "nu-over" : ""}>{kcal(Math.abs(remaining))}</strong>
              <span className="muted">{over ? "kcal de más" : "kcal restantes"}</span>
            </>
          ) : (
            <span className="muted">Sin objetivo calculado</span>
          )}
        </div>
      </div>

      <p className="nu-exact muted">
        <span className="nu-exact-dot ok" /> exacto {kcal(data.exactKcal)} kcal ·{" "}
        <span className="nu-exact-dot est" /> estimado {kcal(data.estimatedKcal)} kcal
      </p>

      <div className="nu-macros">
        <MacroBar label="Proteína" value={totals.proteinG} target={target?.proteinG ?? null} />
        <MacroBar label="Hidratos" value={totals.carbsG} target={target?.carbsG ?? null} />
        <MacroBar label="Grasas" value={totals.fatG} target={target?.fatG ?? null} />
      </div>

      {data.missingProfile.length > 0 && (
        <p className="nu-warn">
          Para calcular tu objetivo falta: {data.missingProfile.join(", ")}.{" "}
          <Link href="/cuenta/perfil">Completar perfil →</Link>
        </p>
      )}

      {target && (
        <>
          <button type="button" className="secondary nu-toggle" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
            {open ? "Ocultar desglose" : "¿Cómo se calcula tu objetivo?"}
          </button>
          {open && (
            <div className="nu-breakdown">
              <dl>
                <dt>Metabolismo basal</dt>
                <dd>{kcal(target.bmr)} kcal</dd>
                {target.activityMode === "estimado" ? (
                  <>
                    <dt>Actividad estimada (con deporte)</dt>
                    <dd>+{kcal(target.dailyActivityKcal)} kcal</dd>
                  </>
                ) : (
                  <>
                    <dt>Actividad diaria (sin entrenar)</dt>
                    <dd>+{kcal(target.dailyActivityKcal)} kcal</dd>
                    <dt>Entrenos de hoy</dt>
                    <dd>+{kcal(target.trainingKcal)} kcal</dd>
                  </>
                )}
                <dt className="nu-sum">Mantenimiento</dt>
                <dd className="nu-sum">{kcal(target.maintenanceKcal)} kcal</dd>
                <dt>Ajuste por objetivo</dt>
                <dd>
                  {target.adjustmentKcal > 0 ? "+" : ""}
                  {kcal(target.adjustmentKcal)} kcal
                </dd>
                <dt className="nu-sum">Objetivo del día</dt>
                <dd className="nu-sum">{kcal(target.targetKcal)} kcal</dd>
              </dl>
              {target.rateKgWeek !== 0 && (
                <p className="muted nu-note">
                  Ritmo previsto: {g1(Math.abs(target.rateKgWeek))} kg/semana{" "}
                  {target.rateKgWeek < 0 ? "de pérdida" : "de ganancia"}.
                </p>
              )}
              {target.notes.length > 0 && (
                <ul className="nu-notes">
                  {target.notes.map((n, i) => (
                    <li key={i}>{n}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
