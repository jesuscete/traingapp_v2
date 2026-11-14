import assert from "node:assert/strict";
import { test } from "node:test";

import { parseInline, parseMarkdown } from "@/lib/markdown";

test("negrita, cursiva y código en línea", () => {
  assert.deepEqual(parseInline("Haz **4x8** de *sentadilla* con `RPE 8`"), [
    { kind: "text", text: "Haz " },
    { kind: "strong", text: "4x8" },
    { kind: "text", text: " de " },
    { kind: "em", text: "sentadilla" },
    { kind: "text", text: " con " },
    { kind: "code", text: "RPE 8" },
  ]);
});

test("asteriscos sueltos y snake_case no se interpretan", () => {
  assert.deepEqual(parseInline("3 * 4 = 12"), [{ kind: "text", text: "3 * 4 = 12" }]);
  assert.deepEqual(parseInline("press_banca_plano"), [{ kind: "text", text: "press_banca_plano" }]);
});

test("el HTML queda como texto", () => {
  assert.deepEqual(parseInline("<b>hola</b>"), [{ kind: "text", text: "<b>hola</b>" }]);
});

test("párrafos, títulos y listas", () => {
  const blocks = parseMarkdown("## Plan\nHoy toca:\n- **Pierna**\n- Core\n  con plancha\n\n1. Calentar\n2. Series");
  assert.equal(blocks.length, 4);
  assert.deepEqual(blocks[0], { kind: "h", inline: [{ kind: "text", text: "Plan" }] });
  assert.equal(blocks[1].kind, "p");
  assert.ok(blocks[2].kind === "ul" && blocks[2].items.length === 2);
  assert.ok(blocks[2].kind === "ul" && blocks[2].items[1].map((i) => i.text).join("") === "Core con plancha");
  assert.ok(blocks[3].kind === "ol" && blocks[3].items.length === 2);
});
