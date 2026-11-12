"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MiniRing } from "@/components/sport/PrepSummary";
import { api } from "@/lib/api";
import type { SportAnalysis } from "@/lib/types";

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
    const text =
      `Analiza mi rutina "${routineName}" para ${sport} y propón los cambios concretos ` +
      `(sustituir o añadir ejercicios) para cubrir estas carencias: ${gaps.join(", ") || "ninguna relevante"}.`;
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
                  data.gaps.map((g) => (
                    <p key={g.code} style={{ margin: "0 0 0.4rem" }}>
                      {g.message}
                    </p>
                  ))
                )}
              </div>
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
