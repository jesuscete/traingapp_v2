import assert from "node:assert/strict";
import { test } from "node:test";

import { bodyTrend, slopePerWeek } from "@/lib/bodyTrend";
import type { NutritionGoal, WeightPoint } from "@/lib/types";

function series(start: number, perDay: number, days: number[], fat?: (d: number) => number): WeightPoint[] {
  return days.map((d) => ({
    measuredOn: `2026-11-${String(d).padStart(2, "0")}`,
    weightKg: start + perDay * (d - days[0]),
    bodyFatPct: fat ? fat(d) : null,
  }));
}

const goal = (over: Partial<NutritionGoal>): NutritionGoal => ({
  goal: "perder",
  proteinGPerKg: 2,
  activityFactor: 1.4,
  ...over,
});

test("pendiente en unidades por semana; pocos puntos o poco rango → null", () => {
  assert.equal(slopePerWeek([{ x: 0, y: 80 }, { x: 7, y: 79 }]), null);
  assert.equal(slopePerWeek([{ x: 0, y: 80 }, { x: 1, y: 80 }, { x: 2, y: 80 }]), null);
  const s = slopePerWeek([{ x: 0, y: 80 }, { x: 7, y: 79.5 }, { x: 14, y: 79 }]);
  assert.ok(s !== null && Math.abs(s + 0.5) < 1e-9);
});

test("bajando peso y grasa: buena señal", () => {
  const t = bodyTrend(series(82, -0.07, [1, 4, 8, 11, 14], (d) => 20 - d * 0.05), null, "2026-11-14");
  assert.equal(t.weight?.direction, "baja");
  assert.equal(t.fat?.direction, "baja");
  assert.ok(t.summary.includes("grasa bajando"));
  assert.equal(t.goal, null);
});

test("objetivo con fecha: en plazo o tarde", () => {
  const pts = series(82, -0.1, [1, 5, 9, 14]); // -0,7 kg/sem, último 80,7
  const ok = bodyTrend(pts, goal({ targetWeightKg: 78, targetDate: "2027-02-01" }), "2026-11-14");
  assert.equal(ok.goal?.tone, "ok");
  const late = bodyTrend(pts, goal({ targetWeightKg: 70, targetDate: "2026-12-15" }), "2026-11-14");
  assert.equal(late.goal?.tone, "warn");
  assert.ok(late.goal?.text.includes("necesitas"));
});

test("dirección contraria al objetivo", () => {
  const t = bodyTrend(series(80, 0.05, [1, 5, 9, 14]), goal({ targetWeightKg: 75 }), "2026-11-14");
  assert.equal(t.goal?.tone, "bad");
});

test("mantener sin peso objetivo", () => {
  const t = bodyTrend(series(80, 0, [1, 5, 9, 14]), goal({ goal: "mantener" }), "2026-11-14");
  assert.equal(t.weight?.direction, "estable");
  assert.equal(t.goal?.tone, "ok");
});
