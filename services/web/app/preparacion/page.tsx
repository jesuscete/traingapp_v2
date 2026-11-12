"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { ExerciseThumb } from "@/components/gym/ExerciseThumb";
import { AddToRoutineSheet } from "@/components/sport/AddToRoutineSheet";
import { TargetBars } from "@/components/sport/TargetBars";
import { api } from "@/lib/api";
import type {
  GapSeverity,
  SportAnalysis,
  SportNarrative,
  SportSuggestion,
} from "@/lib/types";
import { useToken } from "@/lib/useToken";

const SEVERITIES: { key: GapSeverity; title: string }[] = [
  { key: "alta", title: "Prioridad alta" },
  { key: "media", title: "Prioridad media" },
  { key: "baja", title: "Prioridad baja" },
];

type BasisChoice = "auto" | "historial" | "rutina";
const BASIS_OPTIONS: { key: BasisChoice; label: string }[] = [
  { key: "auto", label: "Automático" },
  { key: "historial", label: "Mi historial" },
  { key: "rutina", label: "Mi rutina" },
];

function ScoreRing({ score }: { score: number }) {
  const radius = 44;
  const circ = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const tone = clamped >= 70 ? "ok" : clamped >= 40 ? "mid" : "low";
  return (
    <div className="m4-ring" role="img" aria-label={`Puntuación ${Math.round(clamped)} de 100`}>
      <svg viewBox="0 0 110 110" width="112" height="112">
        <circle cx="55" cy="55" r={radius} className="m4-ring-bg" />
        <circle
          cx="55"
          cy="55"
          r={radius}
          className={`m4-ring-fg m4-ring-${tone}`}
          strokeDasharray={`${(clamped / 100) * circ} ${circ}`}
          transform="rotate(-90 55 55)"
        />
      </svg>
      <div className="m4-ring-text">
        <strong>{Math.round(clamped)}</strong>
        <span className="muted">/ 100</span>
      </div>
    </div>
  );
}

function PushPull({ data }: { data: SportAnalysis }) {
  const total = data.pushSets + data.pullSets;
  const pushPct = total > 0 ? (data.pushSets / total) * 100 : 50;
  return (
    <div>
      <div className="m4-pp-track" role="img" aria-label="Reparto de series de empuje y tirón">
        <div className="m4-pp-push" style={{ width: `${pushPct}%` }} />
        <div className="m4-pp-pull" style={{ width: `${100 - pushPct}%` }} />
      </div>
      <div className="m4-pp-legend">
        <span>
          <i className="m4-dot m4-dot-push" /> Empuje {Math.round(data.pushSets)} series
        </span>
        <span>
          <i className="m4-dot m4-dot-pull" /> Tirón {Math.round(data.pullSets)} series
        </span>
      </div>
      <p className="muted">
        {data.pullPushRatio == null
          ? "Sin series de empuje para calcular la proporción."
          : `Relación tirón/empuje: ${data.pullPushRatio.toFixed(2)} (lo ideal es ≥ 1).`}
      </p>
    </div>
  );
}

export default function Preparacion() {
  const token = useToken();
  const [basis, setBasis] = useState<BasisChoice>("auto");
  const [data, setData] = useState<SportAnalysis | null>(null);
  const [narrative, setNarrative] = useState<SportNarrative | null>(null);
  const [narrativeState, setNarrativeState] = useState<"idle" | "loading" | "error">("idle");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState<SportSuggestion | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const runId = useRef(0);

  const load = useCallback(async (tk: string, choice: BasisChoice) => {
    const id = ++runId.current;
    setLoading(true);
    setError(null);
    setNarrative(null);
    setNarrativeState("idle");
    try {
      const base = await api.getSportAnalysis(tk, { weeks: 4, basis: choice });
      if (id !== runId.current) return;
      setData(base);
      setLoading(false);
      if (base.basis === "sin_datos") return;
      setNarrativeState("loading");
      try {
        const full = await api.getSportAnalysis(tk, {
          weeks: 4,
          basis: choice,
          narrative: true,
        });
        if (id !== runId.current) return;
        setNarrative(full.narrative);
        setNarrativeState(full.narrative ? "idle" : "error");
      } catch {
        if (id === runId.current) setNarrativeState("error");
      }
    } catch (err) {
      if (id !== runId.current) return;
      setError(err instanceof Error ? err.message : "Error al cargar el análisis");
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void load(token, basis);
  }, [token, basis, load]);

  if (!token) return null;

  const title = `Preparación para ${(data?.label ?? "tu deporte").toLowerCase()}`;
  const basisNote =
    data?.basis === "historial"
      ? `Basado en tus últimas ${data.weeks} semanas`
      : data?.basis === "rutina"
        ? "Basado en tu rutina activa"
        : null;

  return (
    <main className="dashboard m4-page">
      <BottomNav />
      <section className="welcome">
        <h2>{title}</h2>
        <p className="subtitle">Qué te falta para rendir en tu deporte principal.</p>
      </section>

      <div className="m4-toolbar">
        <div className="chips">
          {BASIS_OPTIONS.map((opt) => (
            <button
              key={opt.key}
              type="button"
              className={`chip chip-toggle${basis === opt.key ? " on" : ""}`}
              onClick={() => setBasis(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>
        {basisNote && <p className="muted m4-basis">{basisNote}</p>}
      </div>

      {notice && (
        <p className="ok m4-notice" role="status">
          {notice}
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Analizando…</p>}

      {!loading && data?.basis === "sin_datos" && (
        <section className="block m4-empty">
          <h2>Aún no hay datos</h2>
          <p className="muted">
            Para analizar tu preparación necesito entrenos recientes o una rutina activa. Registra
            un entreno o crea una rutina y vuelve aquí.
          </p>
          <div className="chat-actions">
            <Link className="m4-link-btn" href="/entrenar">
              Entrenar ahora
            </Link>
            <Link className="m4-link-btn secondary" href="/rutinas">
              Crear rutina
            </Link>
          </div>
        </section>
      )}

      {!loading && data && data.basis !== "sin_datos" && (
        <>
          <section className="block m4-hero">
            <ScoreRing score={data.score} />
            <div className="m4-hero-body">
              <h2>Diagnóstico</h2>
              {narrative ? (
                <>
                  <p className="m4-resumen">{narrative.resumen}</p>
                  {narrative.prioridades.length > 0 && (
                    <ol className="m4-prio">
                      {narrative.prioridades.map((p, i) => (
                        <li key={i}>{p}</li>
                      ))}
                    </ol>
                  )}
                  {narrative.source === "fallback" && (
                    <p className="muted m4-small">Resumen automático (sin asistente IA).</p>
                  )}
                </>
              ) : narrativeState === "loading" ? (
                <p className="muted m4-pulse">Generando diagnóstico…</p>
              ) : narrativeState === "error" ? (
                <p className="muted">No se pudo generar el diagnóstico en texto.</p>
              ) : null}
            </div>
          </section>

          <section className="block">
            <h2>Qué mejorar</h2>
            {data.gaps.length === 0 ? (
              <p className="muted">No se detectan carencias importantes. Buen trabajo.</p>
            ) : (
              SEVERITIES.map(({ key, title: groupTitle }) => {
                const gaps = data.gaps.filter((g) => g.severity === key);
                if (gaps.length === 0) return null;
                return (
                  <div key={key} className="m4-gap-group">
                    <h3 className={`m4-sev m4-sev-${key}`}>{groupTitle}</h3>
                    {gaps.map((gap) => (
                      <div key={gap.code} className="m4-gap">
                        <p>{gap.message}</p>
                        {gap.suggestions.length > 0 && (
                          <div className="m4-sugg">
                            {gap.suggestions.map((s) => (
                              <button
                                key={s.exerciseId}
                                type="button"
                                className="m4-sugg-chip"
                                onClick={() => {
                                  setNotice(null);
                                  setAdding(s);
                                }}
                                aria-label={`Añadir ${s.name} a la rutina`}
                              >
                                <ExerciseThumb src={s.imageUrl} size={36} />
                                <span className="m4-sugg-name">{s.name}</span>
                                <span className="m4-sugg-add">+ Añadir a la rutina</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                );
              })
            )}
          </section>

          <section className="block">
            <h2>Patrones de movimiento</h2>
            <TargetBars items={data.patterns} />
          </section>

          <section className="block">
            <h2>Músculos clave</h2>
            <TargetBars items={data.muscles} />
          </section>

          <section className="block">
            <h2>Zonas de repeticiones</h2>
            <TargetBars items={data.repZones} percent />
          </section>

          <section className="block">
            <h2>Equilibrio empuje / tirón</h2>
            <PushPull data={data} />
          </section>
        </>
      )}

      {adding && (
        <AddToRoutineSheet
          token={token}
          suggestion={adding}
          onClose={() => setAdding(null)}
          onAdded={(message) => {
            setAdding(null);
            setNotice(message);
            void load(token, basis);
          }}
        />
      )}
    </main>
  );
}
