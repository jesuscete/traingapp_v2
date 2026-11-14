"use client";

import { useEffect, useState } from "react";

import { MuscleBody } from "@/components/MuscleChart";
import { Card } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { translateMuscleGroup } from "@/lib/labels";
import type { MuscleWeek } from "@/lib/types";

const names = (groups: string[]) => groups.map((g) => translateMuscleGroup(g).toLowerCase()).join(", ");

/** Mini mapa corporal: carga de cada músculo en los últimos 7 días (todos los deportes). */
export function MuscleWeekCard({ token }: { token: string }) {
  const [week, setWeek] = useState<MuscleWeek | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api
      .statsMuscleWeek(token)
      .then(setWeek)
      .catch(() => setFailed(true));
  }, [token]);

  if (failed) return null;
  const trained = (week?.muscles ?? []).filter((m) => m.level !== "none" && m.load > 0);
  const byLoad = [...trained].sort((a, b) => b.load - a.load);

  return (
    <Card title="Carga muscular · 7 días" action={{ label: "Ver fatiga", href: "/progreso?tab=fatiga" }}>
      {!week ? null : trained.length === 0 ? (
        <p className="muted mw-empty">Sin entrenos en los últimos 7 días.</p>
      ) : (
        <div className="mw">
          <div className="mw-body">
            <MuscleBody
              compact
              points={week.muscles.map((m) => ({ muscleGroup: m.muscleGroup, value: m.relative }))}
            />
          </div>
          <div className="mw-text">
            {week.high.length > 0 && (
              <p className="mw-flag high">
                <b>Carga alta:</b> {names(week.high)}
              </p>
            )}
            {week.low.length > 0 && (
              <p className="mw-flag low">
                <b>Carga baja:</b> {names(week.low)}
              </p>
            )}
            {week.high.length === 0 && week.low.length === 0 && (
              <p className="mw-flag ok">
                <b>Reparto equilibrado.</b> Lo que más: {names(byLoad.slice(0, 1).map((m) => m.muscleGroup))}; lo que
                menos: {names(byLoad.slice(-1).map((m) => m.muscleGroup))}.
              </p>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}
