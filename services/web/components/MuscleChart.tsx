"use client";

import { useEffect, useMemo, useState } from "react";
import Body, { type ExtendedBodyPart } from "react-muscle-highlighter";

import { RadarChart } from "@/components/RadarChart";
import { mapMuscleGroupToSlug } from "@/lib/muscleSlugMap";

type RadarPoint = { label: string; value: number };
type BodyPoint = { muscleGroup: string; value: number };
type View = "radar" | "body";

const GRADIENT_STOPS = 5;

function hexToRgb(hex: string): [number, number, number] | null {
  const match = /^#?([0-9a-f]{6})$/i.exec(hex.trim());
  if (!match) return null;
  const value = parseInt(match[1], 16);
  return [(value >> 16) & 255, (value >> 8) & 255, value & 255];
}

function rgbToHex(rgb: [number, number, number]): string {
  return (
    "#" +
    rgb
      .map((channel) =>
        Math.round(Math.max(0, Math.min(255, channel)))
          .toString(16)
          .padStart(2, "0"),
      )
      .join("")
  );
}

function gradientStops(from: string, to: string, steps: number): string[] {
  const start = hexToRgb(from);
  const end = hexToRgb(to);
  if (!start || !end || steps < 1) return [];
  return Array.from({ length: steps }, (_, index) => {
    const t = steps === 1 ? 1 : index / (steps - 1);
    return rgbToHex([
      start[0] + (end[0] - start[0]) * t,
      start[1] + (end[1] - start[1]) * t,
      start[2] + (end[2] - start[2]) * t,
    ]);
  });
}

function readThemeVar(name: string): string {
  if (typeof document === "undefined") return "";
  return getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
}

function useThemeColors(): {
  colors: string[];
  defaultFill: string;
  border: string;
} {
  const [, setTick] = useState(0);
  useEffect(() => {
    const refresh = () => setTick((value) => value + 1);
    refresh();
    const observer = new MutationObserver(refresh);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => observer.disconnect();
  }, []);
  return {
    colors: gradientStops(
      readThemeVar("--text-secondary"),
      readThemeVar("--error"),
      GRADIENT_STOPS,
    ),
    defaultFill: readThemeVar("--surface-alt"),
    border: readThemeVar("--border") || "none",
  };
}

function intensityFor(value: number): number {
  const activation = Math.max(0, Math.min(1, value));
  return Math.max(
    1,
    Math.min(
      GRADIENT_STOPS,
      1 + Math.round(activation * (GRADIENT_STOPS - 1)),
    ),
  );
}

function MuscleBody({ points }: { points: BodyPoint[] }) {
  const { colors, defaultFill, border } = useThemeColors();

  const { parts, unmapped } = useMemo(() => {
    const mapped: ExtendedBodyPart[] = [];
    const missing: string[] = [];
    for (const point of points) {
      const slug = mapMuscleGroupToSlug(point.muscleGroup);
      if (!slug) {
        missing.push(point.muscleGroup);
        continue;
      }
      mapped.push({ slug, intensity: intensityFor(point.value) });
    }
    return { parts: mapped, unmapped: missing };
  }, [points]);

  useEffect(() => {
    if (unmapped.length > 0 && process.env.NODE_ENV !== "production") {
      console.warn(
        "[muscleSlugMap] grupos musculares sin Slug en react-muscle-highlighter (no se pintan):",
        unmapped.join(", "),
      );
    }
  }, [unmapped]);

  if (parts.length === 0) return null;

  return (
    <div className="bodymap">
      <div className="bodymap-figure">
        <Body
          side="front"
          data={parts}
          colors={colors}
          defaultFill={defaultFill}
          border={border}
          scale={0.65}
        />
        <p className="muted">Frente</p>
      </div>
      <div className="bodymap-figure">
        <Body
          side="back"
          data={parts}
          colors={colors}
          defaultFill={defaultFill}
          border={border}
          scale={0.65}
        />
        <p className="muted">Espalda</p>
      </div>
    </div>
  );
}

export function MuscleChart({
  radarData,
  bodyPoints,
  size = 320,
  showRadarLabels = false,
}: {
  radarData: RadarPoint[];
  bodyPoints: BodyPoint[];
  size?: number;
  showRadarLabels?: boolean;
}) {
  const hasRadar = radarData.length > 0;
  const hasBody = bodyPoints.length > 0;
  const [view, setView] = useState<View>("radar");

  if (!hasRadar && !hasBody) return null;

  const active: View =
    view === "radar" ? (hasRadar ? "radar" : "body") : hasBody ? "body" : "radar";

  return (
    <div className="muscle-chart">
      <div className="chips" role="tablist" aria-label="Vista de la métrica muscular">
        <button
          type="button"
          role="tab"
          aria-selected={active === "radar"}
          className={`chip chip-toggle ${active === "radar" ? "on" : ""}`}
          onClick={() => setView("radar")}
          disabled={!hasRadar}
        >
          Radar
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={active === "body"}
          className={`chip chip-toggle ${active === "body" ? "on" : ""}`}
          onClick={() => setView("body")}
          disabled={!hasBody}
        >
          Cuerpo
        </button>
      </div>
      <div className="muscle-chart-body">
        {active === "radar" ? (
          <RadarChart data={radarData} size={size} showLabels={showRadarLabels} />
        ) : (
          <MuscleBody points={bodyPoints} />
        )}
      </div>
    </div>
  );
}
