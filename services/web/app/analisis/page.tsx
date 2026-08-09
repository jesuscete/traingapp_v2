"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { LineChart } from "@/components/LineChart";
import { api } from "@/lib/api";
import { translateMuscleGroup } from "@/lib/labels";
import type { FatigueSeries, Load, User } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const PERIODS = [
  { days: 7, label: "7 días" },
  { days: 14, label: "14 días" },
  { days: 30, label: "30 días" },
  { days: 90, label: "90 días" },
];

function shortDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}`;
}

function fatigueLine(series: FatigueSeries["series"]) {
  return {
    labels: series.map((day) => shortDate(day.date)),
    avg: series.map((day) => day.avgFatigue),
    max: series.map((day) => day.maxFatigue),
  };
}

function loadPercent(muscles: Load["byMuscleGroup"]): number {
  const values = muscles.map((m) => m.accumulatedLoad);
  return values.length ? Math.max(...values) : 0;
}

export default function Analisis() {
  const router = useRouter();
  const [token, setToken] = useState<string | null>(null);
  const [days, setDays] = useState(30);
  const [series, setSeries] = useState<FatigueSeries | null>(null);
  const [load, setLoad] = useState<Load | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setToken(stored);
  }, [router]);

  const loadData = useCallback(
    async (token: string, days: number) => {
      setLoading(true);
      setError(null);
      try {
        const [seriesRes, loadRes] = await Promise.all([
          api.statsFatigueSeries(token, days),
          api.statsLoad(token, days),
        ]);
        setSeries(seriesRes);
        setLoad(loadRes);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al cargar análisis");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (token) loadData(token, days);
  }, [token, days, loadData]);

  if (!token) return null;

  const chart = series ? fatigueLine(series.series) : null;
  const maxLoad = load ? loadPercent(load.byMuscleGroup) : 0;

  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Análisis</h2>
        <p className="subtitle">
          Fatiga acumulada y carga de entrenamiento del periodo.
        </p>
      </section>

      <p className="block">
        <Link className="back-link" href="/fatiga">
          Ver detalle de fatiga muscular →
        </Link>
      </p>

      <div className="fatigue-toolbar">
        <span className="muted">Periodo:</span>
        <div className="chips">
          {PERIODS.map((period) => (
            <button
              key={period.days}
              type="button"
              className={`chip chip-toggle${period.days === days ? " on" : ""}`}
              onClick={() => setDays(period.days)}
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Cargando…</p>}

      {!loading && series && load && (
        <>
          <section className="stats">
            <div className="stat-card">
              <span className="stat-label">Carga total</span>
              <span className="stat-value">
                {load.totalLoad ? Math.round(load.totalLoad) : "—"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Monotonía</span>
              <span className="stat-value">
                {load.monotony ? load.monotony.toFixed(2) : "—"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Strain</span>
              <span className="stat-value">
                {load.strain ? Math.round(load.strain) : "—"}
              </span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Fatiga media</span>
              <span className="stat-value">
                {series.series.length
                  ? `${Math.round(
                      series.series.reduce((acc, d) => acc + d.avgFatigue, 0) /
                        series.series.length,
                    )}%`
                  : "—"}
              </span>
            </div>
          </section>

          {chart && (
            <section className="block">
              <h2>Fatiga (media y pico)</h2>
              <LineChart
                labels={chart.labels}
                series={[
                  { name: "media", color: "var(--accent)", points: chart.avg },
                  { name: "pico", color: "var(--error)", points: chart.max },
                ]}
                min={0}
                max={100}
              />
              <div className="fatigue-scale">
                <span className="scale-ok">● media</span>
                <span className="scale-danger">● pico</span>
              </div>
            </section>
          )}

          <section className="block">
            <h2>Carga por grupo muscular</h2>
            {load.byMuscleGroup.length === 0 ? (
              <p className="muted">Sin datos en el periodo.</p>
            ) : (
              <div className="bars">
                {load.byMuscleGroup.map((muscle) => (
                  <div key={muscle.muscleGroup} className="bar-row">
                    <span className="bar-label">
                      {translateMuscleGroup(muscle.muscleGroup)}
                    </span>
                    <div className="bar-track">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${maxLoad ? (muscle.accumulatedLoad / maxLoad) * 100 : 0}%`,
                        }}
                      />
                    </div>
                    <span className="bar-value">
                      {Math.round(muscle.accumulatedLoad)}
                      <span className="muted">
                        {" "}
                        · rec {muscle.recovery.toFixed(0)}%
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
