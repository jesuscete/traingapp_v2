import assert from "node:assert/strict";
import { test } from "node:test";

import { inSentence, summarizeToday } from "@/lib/todayDone";
import type { SessionSummary } from "@/lib/types";

function session(over: Partial<SessionSummary>): SessionSummary {
  return {
    id: Math.random().toString(36),
    discipline: "gym",
    rawText: "",
    performedAt: "2026-11-14T10:00:00Z",
    durationMinutes: 60,
    volumeKg: 0,
    estimatedKcal: null,
    ...over,
  };
}

test("sin sesiones no hay resumen", () => {
  assert.equal(summarizeToday([]), null);
});

test("título según la disciplina, respetando siglas", () => {
  assert.equal(inSentence("HYROX"), "HYROX");
  assert.equal(inSentence("CrossFit"), "CrossFit");
  assert.equal(inSentence("Boxeo"), "boxeo");
  assert.equal(summarizeToday([session({ discipline: "hyrox" })])?.title, "¡Buen entreno de HYROX!");
  assert.equal(summarizeToday([session({ discipline: "boxing" })])?.title, "¡Buen entreno de boxeo!");
  assert.equal(summarizeToday([session({ discipline: "other" })])?.title, "¡Buen entreno!");
});

test("doble sesión: suma totales, icono del entreno más largo y FC ponderada", () => {
  const done = summarizeToday([
    session({ discipline: "gym", durationMinutes: 30, volumeKg: 5000, estimatedKcal: 200 }),
    session({ discipline: "boxing", durationMinutes: 90, estimatedKcal: 700, avgHeartRate: 150 }),
  ]);
  assert.ok(done);
  assert.equal(done.title, "¡Buen día: boxeo y gimnasio!");
  assert.equal(done.mainDiscipline, "boxing");
  assert.equal(done.minutes, 120);
  assert.equal(done.kcal, 900);
  assert.equal(done.volumeKg, 5000);
  assert.equal(done.avgHeartRate, 150);
});
