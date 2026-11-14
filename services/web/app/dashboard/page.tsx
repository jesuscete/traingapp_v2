"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, BedDouble, CheckCircle2, ChevronRight, Flame, Lightbulb, type LucideIcon } from "lucide-react";

import { api } from "@/lib/api";
import { BottomNav } from "@/components/BottomNav";
import { GoalKindIcon, countdownLabel } from "@/components/goals";
import { DisciplineIcon } from "@/components/icons";
import { MuscleBody } from "@/components/MuscleChart";
import { MiniRing } from "@/components/sport/PrepSummary";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatTile } from "@/components/ui/StatTile";
import { NextSteps } from "@/components/onboarding/NextSteps";
import { WelcomeModal } from "@/components/onboarding/WelcomeModal";
import { formatDuration } from "@/lib/format";
import { formatDistance } from "@/lib/metrics";
import { translateDiscipline } from "@/lib/labels";
import { macroFlag } from "@/lib/macros";
import { summarizeToday } from "@/lib/todayDone";
import { kcal as fmtKcal, shortDate, toISODate, todayISO } from "@/lib/nutrition";
import type {
  Fatigue,
  HomeInsight,
  HomeSummary,
  NutritionDay,
  Onboarding,
  SportAnalysis,
  SessionSummary,
  User,
} from "@/lib/types";
import { useToken } from "@/lib/useToken";

const USER_KEY = "traingapp_user";

const KIND_ICON: Record<HomeInsight["kind"], LucideIcon> = {
  good: CheckCircle2,
  warning: AlertTriangle,
  rest: BedDouble,
  tip: Lightbulb,
};

function InsightRow({ item }: { item: HomeInsight }) {
  const body = (
    <>
      {(() => {
        const Icon = KIND_ICON[item.kind];
        return <Icon size={20} strokeWidth={1.75} aria-hidden="true" />;
      })()}
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

const WEEK_LETTERS = ["L", "M", "X", "J", "V", "S", "D"];

/** Fecha local (no UTC) de un instante ISO: un entreno a las 00:30 cuenta para ese día. */
function localISO(instant: string): string {
  return toISODate(new Date(instant));
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
  const [prep, setPrep] = useState<SportAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [onboarding, setOnboarding] = useState<Onboarding | null>(null);
  const [welcomeHidden, setWelcomeHidden] = useState(false);
  const [stepsHidden, setStepsHidden] = useState(false);
  const [showAllInsights, setShowAllInsights] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const loadOnboarding = useCallback(() => {
    if (!token) return;
    api.getOnboarding(token).then(setOnboarding).catch(() => setOnboarding(null));
    api.getProfile(token).then(setUser).catch(() => undefined);
  }, [token]);

  useEffect(() => {
    try {
      setWelcomeHidden(sessionStorage.getItem("traingapp_welcome_hidden") === "1");
      setStepsHidden(sessionStorage.getItem("traingapp_steps_hidden") === "1");
    } catch {
      setWelcomeHidden(false);
    }
  }, []);

  useEffect(() => {
    loadOnboarding();
  }, [loadOnboarding]);

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
    setError(null);
    const load = () => {
      api
        .getHome(token, new Date().getHours(), todayISO())
        .then(setHome)
        .catch((err) => setError(err instanceof Error ? err.message : "Error al cargar datos"));
      api.getSportAnalysis(token, { weeks: 4 }).then(setPrep).catch(() => setPrep(null));
      api.statsFatigue(token).then(setFatigue).catch(() => setFatigue(null));
      api.getNutritionDay(token, todayISO()).then(setMealsToday).catch(() => setMealsToday(null));
      api
        .listSessions(token, { page: 1, pageSize: 20 })
        .then((p) => setRecent(p.items))
        .catch(() => setRecent([]));
    };
    load();
    // Garmin: al abrir la app se sincroniza si hace >15 min; si llega algo nuevo, se recarga.
    api
      .garminStatus(token)
      .then((s) => (s.connected ? api.garminSync(token, { ifStale: true }) : null))
      .then((r) => {
        if (r && (r.imported > 0 || r.healthDays > 0)) load();
      })
      .catch(() => undefined);
  }, [token, reloadKey]);

  const bodyPoints = useMemo(
    () =>
      (fatigue?.muscles ?? []).map((m) => ({
        muscleGroup: m.muscleGroup,
        value: Math.max(0, Math.min(1, m.fatigue / 100)),
      })),
    [fatigue?.muscles],
  );

  const target = mealsToday?.target ?? null;
  const mealsFlag = mealsToday && target ? macroFlag(mealsToday.totals, target, new Date().getHours()) : null;

  const allInsights = home?.insights ?? [];
  const restItem = allInsights.find((i) => i.kind === "rest");
  const warnItem = allInsights.find((i) => i.kind === "warning");
  const hero = restItem
    ? { title: "Día de descanso o suave", text: restItem.title }
    : warnItem
      ? { title: "Entreno suave", text: warnItem.title }
      : { title: "Toca entrenar", text: home?.sportLabel ?? "" };
  const goal = home?.primaryGoal ?? null;
  const goalCountdown = goal ? countdownLabel(goal.daysLeft) : null;
  const active = new Set(home?.activeDays ?? []);
  // Semana natural L-D: los días hasta hoy caen siempre dentro de los 7 que trae activeDays.
  const today = todayISO();
  const weekDays = Array.from({ length: 7 }, (_, k) => {
    const now = new Date();
    const mondayOffset = (now.getDay() + 6) % 7;
    return toISODate(new Date(now.getFullYear(), now.getMonth(), now.getDate() - mondayOffset + k));
  });
  const weekAgo = toISODate(new Date(Date.now() - 6 * 86_400_000));
  const lastWeek = recent.filter((s) => localISO(s.performedAt) >= weekAgo);
  const todaySessions = recent.filter((s) => localISO(s.performedAt) === today);
  const done = summarizeToday(todaySessions);
  // Con el entreno ya hecho, «hoy toca descanso» deja de tener sentido.
  const insights = done ? allInsights.filter((i) => i.kind !== "rest") : allInsights;
  const shownInsights = showAllInsights ? insights : insights.slice(0, 3);
  const burnedToday = done?.kcal ?? 0;
  const weekKcal = lastWeek.reduce((sum, s) => sum + (s.estimatedKcal ?? 0), 0);

  function dismissSteps() {
    try {
      sessionStorage.setItem("traingapp_steps_hidden", "1");
    } catch {
      // sin sessionStorage
    }
    setStepsHidden(true);
  }

  return (
    <main className="dashboard">
      <BottomNav />

      <div className="hoy-head">
        <h2>Hola{user?.name ? `, ${user.name}` : ""}</h2>
        {home && (
          <Link className="hoy-goal" href="/cuenta/objetivos">
            {goal ? (
              <>
                <GoalKindIcon kind={goal.kind} />
                <span>
                  {goal.title}
                  {goalCountdown ? ` · ${goalCountdown}` : ""}
                </span>
              </>
            ) : (
              <span>Define tu objetivo</span>
            )}
            <ChevronRight size={16} strokeWidth={1.75} aria-hidden="true" />
          </Link>
        )}
      </div>

      {error && (
        <p className="hoy-error">
          <span>{error}</span>
          <Button variant="text" onClick={() => setReloadKey((k) => k + 1)}>
            Reintentar
          </Button>
        </p>
      )}

      {token && onboarding && !onboarding.complete && !welcomeHidden && (
        <WelcomeModal
          token={token}
          user={user}
          onboarding={onboarding}
          onSaved={loadOnboarding}
          onDismiss={() => {
            try {
              sessionStorage.setItem("traingapp_welcome_hidden", "1");
            } catch {
              // sin sessionStorage
            }
            setWelcomeHidden(true);
          }}
        />
      )}

      {!home && !error && (
        <>
          <Skeleton height={190} />
          <div className="hoy-grid">
            <Skeleton height={170} />
            <Skeleton height={170} />
            <Skeleton height={120} />
            <Skeleton height={120} />
          </div>
        </>
      )}

      <div className="hoy-layout">
      {home && (
        <Card variant="raised" className={`hoy-hero${done ? " done" : ""}`}>
          <span className="hoy-hero-kicker">Hoy</span>
          {done ? (
            <>
              <div className="hoy-done-head">
                <span className="hoy-done-icon">
                  <DisciplineIcon discipline={done.mainDiscipline} size={28} />
                </span>
                <h2>{done.title}</h2>
              </div>
              <p>Enhorabuena, el entreno de hoy ya está hecho.</p>
              <div className="ui-stat-row hoy-done-stats">
                {done.minutes > 0 && <StatTile value={formatDuration(done.minutes)} label="duración" />}
                {done.kcal > 0 && <StatTile value={fmtKcal(done.kcal)} label="kcal" />}
                {done.avgHeartRate !== null && <StatTile value={done.avgHeartRate} label="ppm de media" />}
                {done.distanceMeters > 0 && <StatTile value={formatDistance(done.distanceMeters)} label="distancia" />}
                {done.volumeKg > 0 && <StatTile value={`${fmtKcal(done.volumeKg)} kg`} label="volumen" />}
              </div>
              <div className="hoy-hero-actions">
                <Button href={`/entrenos/${done.sessions[0].id}`} variant="secondary" size="lg" fullWidth>
                  {done.sessions.length > 1 ? "Ver entreno principal" : "Ver entreno"}
                </Button>
                <Button href="/registrar" variant="text">
                  Registrar otra actividad
                </Button>
              </div>
            </>
          ) : (
            <>
              <h2>{hero.title}</h2>
              {hero.text && <p>{hero.text}</p>}
              <div className="hoy-hero-actions">
                <Button href="/entrenar" size="lg" fullWidth>
                  Empezar entreno
                </Button>
                <Button href="/registrar" variant="text">
                  Registrar otra actividad
                </Button>
              </div>
            </>
          )}
          {insights.length > 0 && (
            <div className="hoy-insights">
              {shownInsights.map((item, i) => (
                <InsightRow key={`${item.title}-${i}`} item={item} />
              ))}
              {insights.length > 3 && (
                <Button variant="text" className="ui-more" onClick={() => setShowAllInsights((v) => !v)}>
                  {showAllInsights ? "Ver menos" : `Ver todos (${insights.length})`}
                </Button>
              )}
            </div>
          )}
        </Card>
      )}

      {token && onboarding && !stepsHidden && (
        <div className="hoy-steps">
          <NextSteps
            token={token}
            onboarding={onboarding}
            skipped={user?.onboardingSkipped ?? []}
            onChanged={loadOnboarding}
            onDismiss={dismissSteps}
          />
        </div>
      )}

      {home && (
        <div className="hoy-grid">
          <Card>
            <Link className="hoy-tile" href="/progreso?tab=fatiga">
              <span className="hoy-tile-title">Fatiga</span>
              {bodyPoints.length > 0 ? (
                <div className="hoy-tile-body">
                  <MuscleBody points={bodyPoints} compact />
                </div>
              ) : (
                <span className="hoy-tile-sub">Sin datos aún</span>
              )}
            </Link>
          </Card>

          <Card>
            <Link className="hoy-tile" href="/comidas">
              <span className="hoy-tile-title">Comida</span>
              {mealsToday ? (
                <>
                  {target ? (
                    <KcalRing value={mealsToday.totals.kcal} target={target.targetKcal} />
                  ) : (
                    <b>{fmtKcal(mealsToday.totals.kcal)} kcal</b>
                  )}
                  <span className="hoy-tile-sub">
                    Proteína {Math.round(mealsToday.totals.proteinG)}
                    {target ? ` / ${Math.round(target.proteinG)}` : ""} g
                  </span>
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
                  {mealsFlag && <span className="hoy-tile-flag">{mealsFlag}</span>}
                </>
              ) : (
                <span className="hoy-tile-sub">Registra tus comidas</span>
              )}
              <span className="hoy-burned">
                <Flame size={14} strokeWidth={1.75} aria-hidden="true" />
                {burnedToday > 0 ? `${fmtKcal(burnedToday)} kcal quemadas hoy` : "Sin entreno hoy"}
              </span>
            </Link>
          </Card>

          <Card>
            <Link className="hoy-tile" href="/progreso">
              <span className="hoy-tile-title">Semana</span>
              <div className="hm-days">
                {weekDays.map((iso, k) => (
                  <span
                    key={iso}
                    className={`hm-day${iso === today ? " today" : ""}${iso > today ? " future" : ""}`}
                  >
                    <span className={`hm-dot${active.has(iso) ? " on" : ""}`} />
                    {WEEK_LETTERS[k]}
                  </span>
                ))}
              </div>
              <span className="hoy-tile-sub">
                {home.weekSessions} {home.weekSessions === 1 ? "sesión" : "sesiones"} en 7 días · {formatDuration(home.weekMinutes)}
              </span>
            </Link>
          </Card>

          <Card>
            <Link className="hoy-tile" href="/progreso?tab=rendimiento">
              <span className="hoy-tile-title">Preparación</span>
              {prep && prep.basis !== "sin_datos" ? (
                <>
                  <MiniRing score={prep.score} />
                  <span className="hoy-tile-sub">{home.sportLabel ?? prep.label}</span>
                </>
              ) : (
                <span className="hoy-tile-sub">Registra entrenos para ver tu preparación</span>
              )}
            </Link>
          </Card>
        </div>
      )}

      {home && (
        <Card
          className="hoy-lastcard"
          title="Últimos 7 días"
          action={{ label: "Ver historial", href: "/rutinas?tab=historial" }}
        >
          {lastWeek.length === 0 ? (
            <p className="hoy-tile-sub">Sin entrenos esta semana.</p>
          ) : (
            <>
              <ul className="hoy-week">
                {lastWeek.map((s) => (
                  <li key={s.id}>
                    <Link className="hoy-last" href={`/entrenos/${s.id}`}>
                      <DisciplineIcon discipline={s.discipline} />
                      <span className="hoy-last-text">
                        <strong>{translateDiscipline(s.discipline)}</strong>
                        <span>
                          {shortDate(localISO(s.performedAt))}
                          {s.distanceMeters ? ` · ${formatDistance(s.distanceMeters)}` : ""} ·{" "}
                          {formatDuration(s.durationMinutes)}
                        </span>
                      </span>
                      <span className="hoy-kcal">
                        {s.estimatedKcal ? `${fmtKcal(s.estimatedKcal)} kcal` : "—"}
                      </span>
                      <ChevronRight size={18} strokeWidth={1.75} aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ul>
              <p className="hoy-week-total">
                {lastWeek.length} {lastWeek.length === 1 ? "entreno" : "entrenos"} ·{" "}
                <strong>{fmtKcal(weekKcal)} kcal</strong>
              </p>
            </>
          )}
        </Card>
      )}
      </div>
    </main>
  );
}
