import assert from "node:assert/strict";
import { test } from "node:test";

import { dayStatus, macroAdvice, macroBars, macroFlag } from "@/lib/macros";

const TARGET = { proteinG: 150, carbsG: 250, fatG: 70 };

test("estado del día", () => {
  assert.equal(dayStatus(0, 2000, false), "empty");
  assert.equal(dayStatus(1500, 2000, true), "progress");
  assert.equal(dayStatus(1500, 2000, false), "low");
  assert.equal(dayStatus(2000, 2000, false), "ok");
  assert.equal(dayStatus(2400, 2000, false), "high");
});

test("pistas proporcionales al peso del macro y exceso marcado", () => {
  const bars = macroBars({ proteinG: 75, carbsG: 300, fatG: 70 }, TARGET);
  const [p, c, f] = bars;
  // Hidratos es el macro que más kcal aporta: pista más larga.
  assert.ok(c.trackPct > p.trackPct && c.trackPct > f.trackPct);
  assert.equal(c.trackPct, 75);
  assert.ok(Math.abs(p.fillPct - p.trackPct / 2) < 1e-9);
  assert.equal(p.over, false);
  assert.equal(c.over, true);
  assert.ok(c.overPct > 0 && c.overPct <= 25);
  assert.equal(f.overPct, 0);
});

test("consejo: pasado de hidratos y corto de proteína → cena proteica", () => {
  const advice = macroAdvice({ proteinG: 60, carbsG: 300, fatG: 40 }, TARGET, 17);
  assert.ok(advice?.includes("hidratos (+50 g)"));
  assert.ok(advice?.includes("faltan 90 g de proteína"));
});

test("consejo: por la mañana no se agobia", () => {
  assert.equal(macroAdvice({ proteinG: 20, carbsG: 60, fatG: 10 }, TARGET, 9), null);
});

test("consejo: proteína rezagada por la tarde", () => {
  const advice = macroAdvice({ proteinG: 40, carbsG: 200, fatG: 50 }, TARGET, 16);
  assert.ok(advice?.startsWith("Vas corto de proteína"));
});

test("aviso corto para tarjetas", () => {
  assert.equal(macroFlag({ proteinG: 60, carbsG: 300, fatG: 40 }, TARGET, 17), "Pasado en hidratos");
  assert.equal(macroFlag({ proteinG: 40, carbsG: 200, fatG: 50 }, TARGET, 16), "Falta proteína");
  assert.equal(macroFlag({ proteinG: 20, carbsG: 60, fatG: 10 }, TARGET, 9), null);
});
