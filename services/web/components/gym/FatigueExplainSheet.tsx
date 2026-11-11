"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { translateDiscipline, translateMuscleGroup } from "@/lib/labels";
import type { FatigueExplain } from "@/lib/types";

type Props = {
  token: string;
  group: string;
  onClose: () => void;
};

export function FatigueExplainSheet({ token, group, onClose }: Props) {
  const [data, setData] = useState<FatigueExplain | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getFatigueExplain(token, group)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Error al cargar");
      });
    return () => {
      cancelled = true;
    };
  }, [token, group]);

  const name = translateMuscleGroup(group);
  const maxRemaining = Math.max(0, ...(data?.sessions.map((s) => s.remaining) ?? [0]));

  return (
    <div
      className="sheet-backdrop"
      role="dialog"
      aria-modal="true"
      aria-label={`¿Por qué tengo fatiga en ${name}?`}
      onClick={onClose}
    >
      <div className="sheet m3-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h3>¿Por qué tengo fatiga en {name.toLowerCase()}?</h3>
          <button type="button" className="sheet-close" aria-label="Cerrar" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="sheet-body">
          {error ? (
            <p className="error">{error}</p>
          ) : !data ? (
            <p className="muted">Cargando...</p>
          ) : data.sessions.length === 0 ? (
            <p className="muted m3-empty">
              No hay sesiones recientes que expliquen fatiga en este músculo.
            </p>
          ) : (
            <>
              <p className="muted">Fatiga actual: {Math.round(data.fatigue)}/100. Sesiones que más pesan:</p>
              <ul className="m3-explain">
                {data.sessions.map((item) => (
                  <li key={item.sessionId}>
                    <Link href={`/entrenos/${item.sessionId}`} className="m3-explain-link">
                      <div className="m3-explain-top">
                        <strong>{translateDiscipline(item.discipline)}</strong>
                        <span className="muted">{item.performedOn}</span>
                      </div>
                      {item.label && <div className="m3-explain-label">{item.label}</div>}
                      <div className="m3-explain-bar">
                        <div className="bar-track">
                          <div
                            className="bar-fill"
                            style={{
                              width: `${maxRemaining > 0 ? (item.remaining / maxRemaining) * 100 : 0}%`,
                            }}
                          />
                        </div>
                        <span className="m3-explain-share">{Math.round(item.share * 100)}%</span>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
