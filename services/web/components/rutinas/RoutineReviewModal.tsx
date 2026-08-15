"use client";

import { useEffect, useMemo, useState } from "react";

import { MuscleChart } from "@/components/MuscleChart";
import { MuscleFatigueMini } from "@/components/gym/MuscleFatigueMini";
import { api } from "@/lib/api";
import {
  buildReviewItems,
  buildZoneReviews,
  computeMuscleImpacts,
  computeZoneTotals,
  detectImbalances,
  type ReviewDay,
} from "@/lib/routineReview";
import type { CatalogExercise, Discipline, RoutineReview } from "@/lib/types";

type Props = {
  days: ReviewDay[];
  routineName?: string;
  token: string;
  catalog?: CatalogExercise[];
  disciplines?: Discipline[];
  onClose: () => void;
};

export function RoutineReviewModal({
  days,
  routineName,
  token,
  catalog: providedCatalog,
  disciplines: providedDisciplines,
  onClose,
}: Props) {
  const [catalog, setCatalog] = useState<CatalogExercise[]>(providedCatalog ?? []);
  const [disciplines, setDisciplines] = useState<Discipline[]>(providedDisciplines ?? []);
  const [server, setServer] = useState<RoutineReview | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  useEffect(() => {
    if (providedCatalog) return;
    api.listCatalogExercises(token).then(setCatalog).catch(() => setCatalog([]));
  }, [token, providedCatalog]);

  useEffect(() => {
    if (providedDisciplines) return;
    api.listDisciplines(token).then(setDisciplines).catch(() => setDisciplines([]));
  }, [token, providedDisciplines]);

  const stats = useMemo(() => {
    const totals = computeZoneTotals(days, catalog, disciplines);
    return {
      radar: buildZoneReviews(totals),
      warnings: detectImbalances(totals),
      impacts: computeMuscleImpacts(days, catalog, disciplines),
      empty: Object.keys(totals.byGroup).length === 0,
    };
  }, [days, catalog, disciplines]);

  useEffect(() => {
    if (stats.empty) return;
    let cancelled = false;
    setAiLoading(true);
    setAiError(null);
    setServer(null);
    api
      .reviewRoutine(token, {
        routineName: (routineName ?? "").trim() || "Rutina",
        days: buildReviewItems(days, catalog, disciplines),
      })
      .then((result) => {
        if (!cancelled) setServer(result);
      })
      .catch((err) => {
        if (!cancelled) {
          setAiError(
            err instanceof Error ? err.message : "Error al generar la evaluación",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setAiLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token, routineName, days, catalog, disciplines, stats.empty]);

  return (
    <div className="picker-overlay" onClick={onClose}>
      <div
        className="picker-modal review-modal"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="picker-header">
          <h2>Revisar: {routineName ?? "rutina"}</h2>
          <button type="button" className="link" onClick={onClose}>
            Cerrar
          </button>
        </div>

        {stats.empty ? (
          <p className="muted" style={{ margin: "0.5rem 1.1rem" }}>
            Añade ejercicios o disciplinas a algunos días para generar el análisis.
          </p>
        ) : (
          <>
            <div className="review-radar">
              <h3>Equilibrio muscular semanal</h3>
              <div className="muscle-grid">
                {(stats.radar.length >= 3 || stats.impacts.length > 0) && (
                  <div className="muscle-radar">
                    <MuscleChart
                      size={360}
                      showRadarLabels
                      radarData={stats.radar.map(({ label, value }) => ({
                        label,
                        value,
                      }))}
                      bodyPoints={stats.impacts.map(({ muscleGroup, activation }) => ({
                        muscleGroup,
                        value: activation,
                      }))}
                    />
                  </div>
                )}
                <MuscleFatigueMini impacts={stats.impacts} />
              </div>
            </div>

            {stats.warnings.length > 0 && (
              <div className="review-warnings">
                <h3>Avisos</h3>
                <ul>
                  {stats.warnings.map((warning) => (
                    <li
                      key={`${warning.kind}-${warning.muscleGroup}`}
                      className={warning.kind === "overload" ? "review-warn-over" : "review-warn-under"}
                    >
                      {warning.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        <div className="review-server">
          <h3>Evaluación por IA</h3>
          {stats.empty ? (
            <p className="muted">
              El radar y los avisos ya se calculan en local. Guarda la rutina para
              obtener la evaluación por IA.
            </p>
          ) : aiLoading ? (
            <p className="muted">Generando evaluación por IA...</p>
          ) : aiError ? (
            <>
              <p className="error">No se pudo generar la evaluación: {aiError}</p>
              <p className="muted">
                El radar y los avisos de carga siguen siendo válidos.
              </p>
            </>
          ) : server ? (
            <>
              {server.puntosFuertes.length > 0 && (
                <>
                  <h4>Puntos fuertes</h4>
                  <ul>
                    {server.puntosFuertes.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
              {server.solapamientos.length > 0 && (
                <>
                  <h4>Solapamientos</h4>
                  {server.solapamientos.map((solape, index) => (
                    <div key={index} className="review-solape">
                      {solape.dias.length > 0 && (
                        <p className="muted">{solape.dias.join(" · ")}</p>
                      )}
                      <p>{solape.descripcion}</p>
                      {solape.grupos.length > 0 && (
                        <p className="muted">{solape.grupos.join(", ")}</p>
                      )}
                    </div>
                  ))}
                </>
              )}
              {server.sugerencias.length > 0 && (
                <>
                  <h4>Sugerencias</h4>
                  <ul>
                    {server.sugerencias.map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}