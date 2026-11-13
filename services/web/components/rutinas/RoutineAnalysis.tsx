"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MiniRing } from "@/components/sport/PrepSummary";
import { api } from "@/lib/api";
import type { RoutineAdherence, SportAnalysis } from "@/lib/types";

const TOP_GAPS = 3;

function AdherenceBlock({ data }: { data: RoutineAdherence }) {
  if (data.sessions === 0) {
    return (
      <div className="ra-box">
        <strong>Plan vs. lo que haces</strong>
        <p className="muted">Aún no hay entrenos de gimnasio registrados para comparar con la rutina.</p>
      </div>
    );
  }
  return (
    <div className="ra-box ra-adherence">
      <strong>Plan vs. lo que haces</strong>
      <p className="muted">
        Últimas {data.weeks.toLocaleString("es-ES")} semanas · {data.sessions}{" "}
        {data.sessions === 1 ? "sesión" : "sesiones"}
      </p>
      <div className="ra-adh-stats">
        <div>
          <b>{data.pct}%</b>
          <span className="muted">de la rutina cumplida</span>
        </div>
        {data.historyScore !== null && (
          <div>
            <b>{data.historyScore}</b>
            <span className="muted">puntuación de lo que entrenas</span>
          </div>
        )}
      </div>
      {data.skipped.length > 0 && (
        <>
          <p className="ra-adh-title">Te estás saltando</p>
          <ul className="ra-adh-list">
            {data.skipped.map((e) => (
              <li key={e.name}>
                {e.name}
                <span className="muted">
                  {e.doneSetsWeek.toLocaleString("es-ES")} / {e.plannedSetsWeek} series/sem
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {data.offPlan.length > 0 && (
        <>
          <p className="ra-adh-title">Haces fuera de la rutina</p>
          <ul className="ra-adh-list">
            {data.offPlan.map((e) => (
              <li key={e.name}>
                {e.name}
                <span className="muted">{e.doneSetsWeek.toLocaleString("es-ES")} series/sem</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="muted ra-adh-note">
        Lo que entrenas de verdad pesa más que lo planificado: si la rutina no encaja, ajústala a lo
        que haces.
      </p>
    </div>
  );
}

type Props = {
  token: string;
  routineId: string;
  routineName: string;
  onClose: () => void;
};

export function RoutineAnalysis({ token, routineId, routineName, onClose }: Props) {
  const router = useRouter();
  const [data, setData] = useState<SportAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [allGaps, setAllGaps] = useState(false);

  useEffect(() => {
    api
      .getSportAnalysis(token, { weeks: 4, basis: "rutina", routineId })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Error al analizar"));
  }, [token, routineId]);

  function prepare() {
    if (!data) return;
    const sport = data.label.toLowerCase();
    const gaps = data.gaps.slice(0, 4).map((g) => g.message);
    const adh = data.adherence;
    const real =
      adh && adh.sessions > 0
        ? ` Ten en cuenta lo que hago de verdad: cumplo un ${adh.pct}% de la rutina` +
          (adh.skipped.length ? `, me salto ${adh.skipped.map((e) => e.name).join(", ")}` : "") +
          (adh.offPlan.length ? ` y hago fuera de ella ${adh.offPlan.map((e) => e.name).join(", ")}` : "") +
          "."
        : "";
    const text =
      `Analiza mi rutina "${routineName}" para ${sport} y propón los cambios concretos ` +
      `(sustituir o añadir ejercicios) para cubrir estas carencias: ${gaps.join(", ") || "ninguna relevante"}.${real}`;
    router.push(`/chat?q=${encodeURIComponent(text)}`);
  }

  return (
    <div className="picker-overlay" onClick={onClose}>
      <div className="picker-modal review-modal" onClick={(event) => event.stopPropagation()}>
        <div className="picker-header">
          <h2>
            Analizar{data ? ` para ${data.label}` : ""}: {routineName}
          </h2>
          <button type="button" className="link" onClick={onClose}>
            Cerrar
          </button>
        </div>
        <div style={{ padding: "0 1.1rem 1.1rem" }}>
          {error && <p className="error">{error}</p>}
          {!data && !error && <p className="muted">Analizando…</p>}
          {data && data.basis === "sin_datos" && (
            <p className="muted">Esta rutina no tiene ejercicios suficientes para analizarla.</p>
          )}
          {data && data.basis !== "sin_datos" && (
            <>
              <div className="hm-prep">
                <MiniRing score={data.score} />
                <p className="muted">Cobertura de la rutina para {data.label.toLowerCase()}.</p>
              </div>
              <div className="ra-box">
                {data.gaps.length === 0 ? (
                  <p className="muted">No se detectan carencias importantes.</p>
                ) : (
                  <>
                    <strong>Lo más importante</strong>
                    {(allGaps ? data.gaps : data.gaps.slice(0, TOP_GAPS)).map((g) => (
                      <p key={g.code} style={{ margin: "0.4rem 0 0" }}>
                        {g.message}
                      </p>
                    ))}
                    {data.gaps.length > TOP_GAPS && (
                      <button type="button" className="link" onClick={() => setAllGaps((v) => !v)}>
                        {allGaps ? "Ver menos" : `Ver ${data.gaps.length - TOP_GAPS} detalles más`}
                      </button>
                    )}
                  </>
                )}
              </div>
              {data.adherence && <AdherenceBlock data={data.adherence} />}
              <div className="chat-actions">
                <button type="button" onClick={prepare}>
                  Preparar rutina con estos cambios
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
