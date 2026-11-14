"use client";

import { useCallback, useEffect, useState } from "react";

import { WeekCard } from "@/components/home/WeekCard";
import { BodyTab } from "@/components/progress/BodyTab";
import { MuscleWeekCard } from "@/components/progress/MuscleWeekCard";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatTile } from "@/components/ui/StatTile";
import { api } from "@/lib/api";
import { formatDuration } from "@/lib/format";
import { todayISO } from "@/lib/nutrition";
import type { HomeSummary } from "@/lib/types";

export function SummaryTab({ token }: { token: string }) {
  const [home, setHome] = useState<HomeSummary | null>(null);
  const [error, setError] = useState(false);

  const load = useCallback(() => {
    setError(false);
    api
      .getHome(token, new Date().getHours(), todayISO())
      .then(setHome)
      .catch(() => setError(true));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  if (error)
    return (
      <p className="error">
        No se pudo cargar el resumen.{" "}
        <button type="button" className="ui-btn text" onClick={load}>
          Reintentar
        </button>
      </p>
    );
  if (!home) return <Skeleton height={180} />;
  const delta =
    home.prevWeekMinutes > 0
      ? Math.round(((home.weekMinutes - home.prevWeekMinutes) / home.prevWeekMinutes) * 100)
      : null;
  return (
    <>
    <Card title="Cómo estás avanzando">
      <div className="ui-stat-row">
        <StatTile value={home.weekSessions} label={home.weekSessions === 1 ? "sesión" : "sesiones"} />
        <StatTile value={formatDuration(home.weekMinutes)} label="esta semana" delta={delta} />
      </div>
      <WeekCard home={home} showDays={false} showTotals={false} />
    </Card>
    <MuscleWeekCard token={token} />
    <BodyTab token={token} />
    </>
  );
}
