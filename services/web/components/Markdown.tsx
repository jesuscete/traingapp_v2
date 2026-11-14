import { Fragment } from "react";

import { parseMarkdown, type Inline } from "@/lib/markdown";

function Spans({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((p, i) =>
        p.kind === "strong" ? (
          <strong key={i}>{p.text}</strong>
        ) : p.kind === "em" ? (
          <em key={i}>{p.text}</em>
        ) : p.kind === "code" ? (
          <code key={i}>{p.text}</code>
        ) : (
          <Fragment key={i}>{p.text}</Fragment>
        ),
      )}
    </>
  );
}

/** Texto del coach con formato básico; nunca inserta HTML. */
export function Markdown({ text }: { text: string }) {
  return (
    <div className="md">
      {parseMarkdown(text).map((b, i) => {
        if (b.kind === "h")
          return (
            <p key={i} className="md-h">
              <Spans parts={b.inline} />
            </p>
          );
        if (b.kind === "p")
          return (
            <p key={i}>
              {b.lines.map((line, j) => (
                <Fragment key={j}>
                  {j > 0 && <br />}
                  <Spans parts={line} />
                </Fragment>
              ))}
            </p>
          );
        const List = b.kind;
        return (
          <List key={i}>
            {b.items.map((item, j) => (
              <li key={j}>
                <Spans parts={item} />
              </li>
            ))}
          </List>
        );
      })}
    </div>
  );
}
