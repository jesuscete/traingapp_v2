"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import {
  ActivityChart,
  formatClock,
  type ChartBand,
  type ChartPoint,
} from "@/components/activity/ActivityChart";
import { api } from "@/lib/api";
import { formatDistance } from "@/lib/metrics";
import type { ActivityDetail, ActivitySummary } from "@/lib/types";

const ZONE_COLORS = ["#9aa0a6", "#3b82f6", "#2fd9a8", "#f5b942", "#ef4444"];
const ZONE_NAMES = ["Z1 Recuperación", "Z2 Aeróbica", "Z3 Tempo", "Z4 Umbral", "Z5 Máximo"];

function num(v: number | null | undefined): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

function lastValue(values: (number | null)[] | undefined): number | null {
  if (!values) return null;
  for (let i = values.length - 1; i >= 0; i--) {
    const v = values[i];
    if (num(v)) return v;
  }
  return null;
}

/** Desnivel positivo con histéresis de 3 m para ignorar el ruido del altímetro. */
function ascent(altitude: (number | null)[] | undefined): number | null {
  if (!altitude) return null;
  let ref: number | null = null;
  let gain = 0;
  for (const a of altitude) {
    if (!num(a)) continue;
    if (ref == null) {
      ref = a;
    } else if (a - ref > 3) {
      gain += a - ref;
      ref = a;
    } else if (ref - a > 3) {
      ref = a;
    }
  }
  return ref == null ? null : Math.round(gain);
}

function paceKind(discipline: string): "run" | "bike" | "swim" | "other" {
  if (discipline === "running") return "run";
  if (discipline === "cycling") return "bike";
  if (discipline === "swimming") return "swim";
  return "other";
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function Zones({ summary }: { summary: ActivitySummary }) {
  const zones = summary.zonesSeconds;
  if (!zones) return null;
  const total = zones.reduce((a, s) => a + s, 0);
  if (total <= 0) return null;
  const { maxEstimated, restingEstimated } = summary.hrProfile;
  return (
    <section className="block">
      <h2>Tiempo en zonas</h2>
      <div className="act-zones">
        {zones.map((seconds, i) => {
          const pct = (seconds / total) * 100;
          const bounds = summary.zoneBounds[i];
          return (
            <div key={i} className="act-zone-row">
              <span className="act-zone-name">
                {ZONE_NAMES[i]}
                {bounds && (
                  <small className="muted">
                    {" "}
                    {Math.round(bounds[0])}–{Math.round(bounds[1])} lpm
                  </small>
                )}
              </span>
              <div className="bar-track">
                <div
                  className="bar-fill"
                  style={{ width: `${pct}%`, background: ZONE_COLORS[i] }}
                />
              </div>
              <span className="act-zone-val">
                {Math.round(seconds / 60)} min · {Math.round(pct)}%
              </span>
            </div>
          );
        })}
      </div>
      <p className="muted act-note">
        Zonas por reserva de FC (FC máx. {summary.hrProfile.maxHr}, reposo{" "}
        {summary.hrProfile.restingHr}).
        {(maxEstimated || restingEstimated) && (
          <>
            {" "}
            {maxEstimated ? "FC máxima estimada" : "FC en reposo estimada"}: añádela en tu{" "}
            <Link href="/perfil">perfil</Link> para zonas precisas.
          </>
        )}
      </p>
    </section>
  );
}

export function ActivitySection({
  token,
  sessionId,
  discipline,
}: {
  token: string;
  sessionId: string;
  discipline: string;
}) {
  const [detail, setDetail] = useState<ActivityDetail | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getActivity(token, sessionId)
      .then((d) => {
        if (!cancelled) setDetail(d);
      })
      .catch(() => {
        if (!cancelled) setDetail(null);
      });
    return () => {
      cancelled = true;
    };
  }, [token, sessionId]);

  const kind = paceKind(discipline);
  const samples = detail?.samples;
  const times = samples?.t;

  const hrPoints = useMemo<ChartPoint[]>(() => {
    if (!times || !samples?.hr) return [];
    const hr = samples.hr;
    return times.map((x, i) => ({ x, y: num(hr[i]) && hr[i]! > 0 ? hr[i] : null }));
  }, [times, samples?.hr]);

  const speedPoints = useMemo<ChartPoint[]>(() => {
    if (!times || !samples?.speed) return [];
    const speed = samples.speed;
    return times.map((x, i) => {
      const v = speed[i];
      if (!num(v) || v < 0.3) return { x, y: null };
      if (kind === "run") return { x, y: 1000 / v };
      if (kind === "swim") return { x, y: 100 / v };
      return { x, y: v * 3.6 };
    });
  }, [times, samples?.speed, kind]);

  const altPoints = useMemo<ChartPoint[]>(() => {
    if (!times || !samples?.altitude) return [];
    const alt = samples.altitude;
    return times.map((x, i) => ({ x, y: num(alt[i]) ? alt[i] : null }));
  }, [times, samples?.altitude]);

  if (!detail || !detail.summary || !times || times.length < 2) return null;
  const summary = detail.summary;

  const distance = summary.distanceM ?? lastValue(samples?.distance);
  const duration = summary.durationS ?? times[times.length - 1];
  const gain = summary.ascentM ?? ascent(samples?.altitude);
  const avgSpeed = distance != null && duration > 0 ? distance / duration : null;

  let paceLabel = "Velocidad media";
  let paceValue: string | null = null;
  if (avgSpeed != null && avgSpeed > 0) {
    if (kind === "run") {
      paceLabel = "Ritmo medio";
      paceValue = `${formatClock(1000 / avgSpeed)} min/km`;
    } else if (kind === "swim") {
      paceLabel = "Ritmo medio";
      paceValue = `${formatClock(100 / avgSpeed)} /100 m`;
    } else {
      paceValue = `${(avgSpeed * 3.6).toFixed(1)} km/h`;
    }
  }

  const bands: ChartBand[] = summary.zoneBounds.map(([from, to], i) => ({
    from,
    to,
    color: ZONE_COLORS[i] ?? ZONE_COLORS[4],
  }));
  const hrValues = hrPoints.filter((p) => p.y != null).map((p) => p.y as number);
  const hrMin = hrValues.length ? Math.floor((Math.min(...hrValues) - 5) / 10) * 10 : 0;
  const hrMax = hrValues.length ? Math.ceil((Math.max(...hrValues) + 5) / 10) * 10 : 0;

  // Ritmo: recorta extremos (paradas, ruido) con percentiles 3-97.
  const speedValues = speedPoints
    .filter((p) => p.y != null)
    .map((p) => p.y as number)
    .sort((a, b) => a - b);
  const pLo = speedValues.length ? speedValues[Math.floor(speedValues.length * 0.03)] : 0;
  const pHi = speedValues.length
    ? speedValues[Math.min(speedValues.length - 1, Math.floor(speedValues.length * 0.97))]
    : 0;
  const isTime = kind === "run" || kind === "swim";

  const cadenceUnit = kind === "run" ? "ppm" : kind === "bike" ? "rpm" : "";

  return (
    <section className="block act-section">
      <h2>Actividad</h2>
      <div className="stats act-stats">
        {distance != null && distance > 0 && (
          <Stat label="Distancia" value={formatDistance(distance)} />
        )}
        <Stat label="Duración" value={formatClock(duration)} />
        {paceValue && <Stat label={paceLabel} value={paceValue} />}
        {num(summary.avgHr) && <Stat label="FC media" value={`${Math.round(summary.avgHr)} lpm`} />}
        {num(summary.maxHr) && <Stat label="FC máx." value={`${Math.round(summary.maxHr)} lpm`} />}
        {gain != null && gain > 0 && <Stat label="Desnivel +" value={`${gain} m`} />}
        {num(summary.avgCadence) && summary.avgCadence > 0 && (
          <Stat
            label="Cadencia media"
            value={`${Math.round(summary.avgCadence)}${cadenceUnit ? ` ${cadenceUnit}` : ""}`}
          />
        )}
        {num(summary.deviceCalories) && summary.deviceCalories > 0 && (
          <Stat label="Calorías (reloj)" value={`${Math.round(summary.deviceCalories)} kcal`} />
        )}
        {num(summary.trimp) && <Stat label="TRIMP" value={String(Math.round(summary.trimp))} />}
      </div>
      {num(summary.trimp) && (
        <p className="muted act-note">
          TRIMP: carga de entrenamiento calculada por frecuencia cardiaca.
        </p>
      )}

      {hrValues.length > 1 && (
        <div className="act-chart-block">
          <h3>Frecuencia cardiaca</h3>
          <ActivityChart
            label="Frecuencia cardiaca en el tiempo"
            points={hrPoints}
            color="#ef4444"
            min={hrMin}
            max={hrMax}
            bands={bands}
            formatY={(v) => String(Math.round(v))}
          />
        </div>
      )}

      {speedValues.length > 1 && (
        <div className="act-chart-block">
          <h3>{isTime ? "Ritmo" : "Velocidad"}</h3>
          <ActivityChart
            label={isTime ? "Ritmo en el tiempo" : "Velocidad en el tiempo"}
            points={speedPoints}
            color="#3b82f6"
            min={pLo}
            max={pHi}
            invert={isTime}
            formatY={(v) => (isTime ? formatClock(v) : String(Math.round(v)))}
          />
          <p className="muted act-note">
            {kind === "run" && "min/km (arriba = más rápido)"}
            {kind === "swim" && "min/100 m (arriba = más rápido)"}
            {!isTime && "km/h"}
          </p>
        </div>
      )}

      {altPoints.some((p) => p.y != null) && (
        <div className="act-chart-block">
          <h3>Perfil de altitud</h3>
          <ActivityChart
            label="Altitud en el tiempo"
            points={altPoints}
            color="#2fd9a8"
            fill
            formatY={(v) => `${Math.round(v)} m`}
          />
        </div>
      )}

      <Zones summary={summary} />

      {summary.kmSplits.length > 0 && (
        <div className="act-chart-block">
          <h3>Parciales por km</h3>
          <table className="plain act-splits">
            <thead>
              <tr>
                <th>Km</th>
                <th>Tiempo</th>
                <th>Ritmo</th>
                <th>FC media</th>
              </tr>
            </thead>
            <tbody>
              {summary.kmSplits.map((s) => (
                <tr key={s.km}>
                  <td>{s.km}</td>
                  <td>{formatClock(s.seconds)}</td>
                  <td>{formatClock(s.paceSPerKm)} /km</td>
                  <td>{s.avgHr != null ? `${s.avgHr} lpm` : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
