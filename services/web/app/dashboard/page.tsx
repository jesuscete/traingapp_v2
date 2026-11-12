"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { BodyMap } from "@/components/BodyMap";
import { BottomNav } from "@/components/BottomNav";
import { WeekCard } from "@/components/home/WeekCard";
import { formatDuration } from "@/lib/format";
import { translateDiscipline } from "@/lib/labels";
import { kcal as fmtKcal, shortDate, todayISO } from "@/lib/nutrition";
import type {
  Fatigue,
  HomeInsight,
  HomeSummary,
  NutritionDay,
  SessionSummary,
  User,
} from "@/lib/types";
import { useToken } from "@/lib/useToken";

const USER_KEY = "traingapp_user";

const KIND_ICON: Record<HomeInsight["kind"], string> = {
  good: "✓",
  warning: "⚠",
  rest: "💤",
  tip: "💡",
};

const DISCIPLINE_ICON: Record<string, string> = {
  gym: "🏋️",
  boxing: "🥊",
  running: "🏃",
  cycling: "🚴",
  swimming: "🏊",
};

function InsightRow({ item }: { item: HomeInsight }) {
  const body = (
    <>
      <span aria-hidden="true">{KIND_ICON[item.kind]}</span>
      <span>
        <strong>{item.title}</strong>
        <span className="d">{item.detail}</span>
      </span>
    </>
  );
  return item.href ? (
    <Link className={`hm-insight ${item.kind}`} href={item.href}>
      {body}
    </Link>
  ) : (
    <div className={`hm-insight ${item.kind}`}>{body}</div>
  );
}

function KcalRing({ value, target }: { value: number; target: number }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const pct = target > 0 ? Math.min(1, value / target) : 0;
  return (
    <div className="hm-ring">
      <svg width="84" height="84" viewBox="0 0 84 84" aria-hidden="true">
        <circle cx="42" cy="42" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx="42"
          cy="42"
          r={r}
          fill="none"
          stroke={value > target ? "var(--warning)" : "var(--accent)"}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`}
          transform="rotate(-90 42 42)"
        />
      </svg>
      <div className="hm-ring-label">
        <b>{fmtKcal(value)}</b>
        <span className="muted">kcal</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const token = useToken();
  const [user, setUser] = useState<User | null>(null);
  const [home, setHome] = useState<HomeSummary | null>(null);
  const [fatigue, setFatigue] = useState<Fatigue | null>(null);
  const [mealsToday, setMealsToday] = useState<NutritionDay | null>(null);
  const [recent, setRecent] = useState<SessionSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(USER_KEY);
      if (stored) setUser(JSON.parse(stored));
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    api
      .getHome(token, new Date().getHours(), todayISO())
      .then(setHome)
      .catch((err) => setError(err instanceof Error ? err.message : "Error al cargar datos"));
    api.statsFatigue(token).then(setFatigue).catch(() => setFatigue(null));
    api.getNutritionDay(token, todayISO()).then(setMealsToday).catch(() => setMealsToday(null));
    api
      .listSessions(token, { page: 1, pageSize: 5 })
      .then((p) => setRecent(p.items))
      .catch(() => setRecent([]));
  }, [token]);

  const bodyPoints = useMemo(
    () =>
      (fatigue?.muscles ?? []).map((m) => ({
        muscleGroup: m.muscleGroup,
        value: Math.max(0, Math.min(1, m.fatigue / 100)),
      })),
    [fatigue?.muscles],
  );

  const target = mealsToday?.target ?? null;

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>Hola{user?.name ? `, ${user.name}` : ""} 👋</h2>
      </section>

      {error && <p className="error">{error}</p>}

      {home && home.insights.length > 0 && (
        <section className="hm-card">
          <h2>Avisos</h2>
          {home.insights.map((item, i) => (
            <InsightRow key={`${item.title}-${i}`} item={item} />
          ))}
        </section>
      )}

      {bodyPoints.length > 0 && (
        <section className="hm-card">
          <h2>
            Fatiga muscular <Link href="/fatiga">Ver detalle</Link>
          </h2>
          <BodyMap points={bodyPoints} showLegend={false} />
        </section>
      )}

      {home && (
        <section className="hm-card">
          <h2>Esta semana</h2>
          <WeekCard home={home} />
        </section>
      )}

      <section className="hm-card">
        <h2>
          Comida de hoy <Link href="/comidas">Abrir</Link>
        </h2>
        {mealsToday ? (
          <Link className="hm-food" href="/comidas">
            {target ? (
              <KcalRing value={mealsToday.totals.kcal} target={target.targetKcal} />
            ) : (
              <b>{fmtKcal(mealsToday.totals.kcal)} kcal</b>
            )}
            <div className="hm-food-bars">
              {target && (
                <p className="muted">
                  {target.targetKcal - mealsToday.totals.kcal >= 0 ? "Quedan" : "Te pasas"}{" "}
                  {fmtKcal(Math.abs(target.targetKcal - mealsToday.totals.kcal))} de{" "}
                  {fmtKcal(target.targetKcal)} kcal
                </p>
              )}
              <p>
                Proteína {Math.round(mealsToday.totals.proteinG)}
                {target ? ` / ${Math.round(target.proteinG)}` : ""} g
              </p>
              {target && (
                <div className="bar-track">
                  <div
                    className="bar-fill"
                    style={{
                      width: `${Math.min(100, (mealsToday.totals.proteinG / Math.max(1, target.proteinG)) * 100)}%`,
                    }}
                  />
                </div>
              )}
            </div>
          </Link>
        ) : (
          <Link className="muted" href="/comidas">
            Registra tus comidas y controla tus kcal →
          </Link>
        )}
      </section>

      {recent.length > 0 && (
        <section className="hm-card">
          <h2>
            Actividad reciente <Link href="/entrenos">Ver todo</Link>
          </h2>
          {recent.map((s) => (
            <Link key={s.id} className="hm-recent" href={`/entrenos/${s.id}`}>
              <span>
                {DISCIPLINE_ICON[s.discipline] ?? "🏅"} {translateDiscipline(s.discipline)}
              </span>
              <span className="muted">
                {shortDate(s.performedAt.slice(0, 10))} · {formatDuration(s.durationMinutes)}
              </span>
            </Link>
          ))}
        </section>
      )}
    </main>
  );
}
