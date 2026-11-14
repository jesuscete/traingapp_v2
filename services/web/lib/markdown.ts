/**
 * Markdown mínimo para las respuestas del coach: negrita, cursiva, código en línea,
 * títulos y listas. Devuelve una estructura (nunca HTML) para pintarla sin riesgo de inyección.
 */

export type Inline = { kind: "text" | "strong" | "em" | "code"; text: string };

export type Block =
  | { kind: "p"; lines: Inline[][] }
  | { kind: "h"; inline: Inline[] }
  | { kind: "ul" | "ol"; items: Inline[][] };

const INLINE = /(\*\*|__)(.+?)\1|`([^`]+)`|(?<![\w*])[*_](?![\s*_])(.+?)(?<![\s*_])[*_](?![\w*])/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", text: text.slice(last, at) });
    if (m[2] !== undefined) out.push({ kind: "strong", text: m[2] });
    else if (m[3] !== undefined) out.push({ kind: "code", text: m[3] });
    else out.push({ kind: "em", text: m[4] });
    last = at + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBERED = /^\s*\d+[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;

export function parseMarkdown(text: string): Block[] {
  const blocks: Block[] = [];
  let para: Inline[][] = [];
  let list: { kind: "ul" | "ol"; items: Inline[][] } | null = null;

  const flush = () => {
    if (para.length) blocks.push({ kind: "p", lines: para });
    if (list) blocks.push(list);
    para = [];
    list = null;
  };

  for (const raw of text.replace(/\r\n/g, "\n").split("\n")) {
    const line = raw.trimEnd();
    if (line.trim() === "") {
      flush();
      continue;
    }
    const heading = HEADING.exec(line);
    const bullet = BULLET.exec(line);
    const numbered = NUMBERED.exec(line);
    if (heading) {
      flush();
      blocks.push({ kind: "h", inline: parseInline(heading[1]) });
    } else if (bullet || numbered) {
      const kind = bullet ? "ul" : "ol";
      if (para.length || (list && list.kind !== kind)) flush();
      list ??= { kind, items: [] };
      list.items.push(parseInline((bullet ?? numbered)![1]));
    } else if (list) {
      // Línea de continuación de un punto de la lista.
      list.items[list.items.length - 1].push(...parseInline(` ${line.trim()}`));
    } else {
      para.push(parseInline(line));
    }
  }
  flush();
  return blocks;
}
