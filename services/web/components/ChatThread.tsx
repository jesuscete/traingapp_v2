"use client";

import Link from "next/link";

import { Markdown } from "@/components/Markdown";

import type { ChatActionState, ChatMessage } from "@/lib/chatStore";
import type { ChatCard } from "@/lib/types";
import { TOOL_LABELS } from "@/lib/useChatEngine";

type Variant = "page" | "widget";

type Props = {
  variant: Variant;
  messages: ChatMessage[];
  busy: boolean;
  onConfirm: (messageId: string, actionId: string) => void;
  onDiscard: (messageId: string, actionId: string) => void;
};

function toolSummary(tools: string[] | undefined): string | null {
  if (!tools || tools.length === 0) return null;
  const labels = [...new Set(tools.map((t) => TOOL_LABELS[t] ?? t))];
  return `Consultado: ${labels.join(", ")}`;
}

function ActionCard({
  action,
  messageId,
  onConfirm,
  onDiscard,
}: {
  action: ChatActionState;
  messageId: string;
  onConfirm: Props["onConfirm"];
  onDiscard: Props["onDiscard"];
}) {
  const open = action.status === "pending" || action.status === "busy";
  return (
    <div className={`m4-action m4-action-${action.status}`}>
      {action.type === "save_meal" && <p className="m4-action-tag">Guardar comida</p>}
      <div className="m4-action-summary">
        <Markdown text={action.summary} />
      </div>
      {open && (
        <div className="m4-action-btns">
          <button
            type="button"
            disabled={action.status === "busy"}
            onClick={() => onConfirm(messageId, action.id)}
          >
            {action.status === "busy" ? "Procesando…" : action.type === "save_meal" ? "Guardar comida" : "Confirmar"}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={action.status === "busy"}
            onClick={() => onDiscard(messageId, action.id)}
          >
            Descartar
          </button>
        </div>
      )}
      {action.status === "done" && (
        <p className="ok m4-action-note">
          {action.result ?? "Hecho."}{" "}
          {action.type === "save_meal" && <Link href="/comidas">Ver comidas →</Link>}
          {action.sessionId && (
            <Link href={`/entrenos/${action.sessionId}`}>Ver entreno →</Link>
          )}
        </p>
      )}
      {action.status === "discarded" && <p className="muted m4-action-note">Descartada.</p>}
      {action.error && action.status !== "done" && (
        <p className="error m4-action-note">{action.error}</p>
      )}
    </div>
  );
}

function barTone(card: ChatCard, value: number): string {
  if (card.type === "fatigue") {
    return value >= 85 ? "danger" : value >= 70 ? "warning" : "ok";
  }
  return value >= 100 ? "ok" : "accent";
}

/** Tarjeta estructurada (rutina, fatiga, ejercicios, comidas) que llega sin pasar por la IA. */
function ChatCardView({ card }: { card: ChatCard }) {
  return (
    <section className={`m10-card m10-card-${card.type}`}>
      <header className="m10-card-head">
        <strong>{card.title}</strong>
        {card.subtitle && <span className="muted">{card.subtitle}</span>}
      </header>
      {card.sections.map((section, index) => (
        <div key={`${section.title ?? "s"}-${index}`} className="m10-card-section">
          {section.title && <p className="m10-card-section-title">{section.title}</p>}
          {section.items.length === 0 && <p className="muted m10-card-empty">—</p>}
          <ul className="m10-card-items">
            {section.items.map((item, itemIndex) => (
              <li key={`${item.title}-${itemIndex}`} className="m10-card-item">
                {item.imageUrl && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.imageUrl} alt="" className="m10-card-img" loading="lazy" />
                )}
                <div className="m10-card-body">
                  <div className="m10-card-row">
                    <span className="m10-card-title">{item.title}</span>
                    {item.badge && <span className="m10-card-badge">{item.badge}</span>}
                  </div>
                  {item.subtitle && <span className="m10-card-sub">{item.subtitle}</span>}
                  {item.value != null && (
                    <span className="m10-card-bar" aria-label={`${Math.round(item.value)} de 100`}>
                      <span
                        className={`m10-card-bar-fill m10-tone-${barTone(card, item.value)}`}
                        style={{ width: `${Math.max(2, Math.min(100, item.value))}%` }}
                      />
                    </span>
                  )}
                  {item.detail && <span className="m10-card-detail muted">{item.detail}</span>}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {card.link && (
        <Link href={card.link} className="m10-card-link">
          {card.linkLabel ?? "Abrir"} →
        </Link>
      )}
    </section>
  );
}

export function ChatThread({ variant, messages, busy, onConfirm, onDiscard }: Props) {
  const bubble = `chat-${variant}-bubble`;
  return (
    <>
      {messages.map((message) => {
        const tools = toolSummary(message.tools);
        return (
          <div key={message.id} className={`m4-msg ${message.role}`}>
            {message.text && (
              <div className={`${bubble} ${message.role}`}>
                {message.role === "user" ? message.text : <Markdown text={message.text} />}
              </div>
            )}
            {message.cards?.map((card, index) => (
              <ChatCardView key={`${message.id}-card-${index}`} card={card} />
            ))}
            {message.actions?.map((action) => (
              <ActionCard
                key={action.id}
                action={action}
                messageId={message.id}
                onConfirm={onConfirm}
                onDiscard={onDiscard}
              />
            ))}
            {tools && (
              <span className="muted m4-tools">
                {tools}
                {message.source === "rules" ? " · al instante, sin IA" : ""}
              </span>
            )}
          </div>
        );
      })}
      {busy && (
        <div className="m4-msg assistant">
          <div className={`${bubble} assistant m4-thinking`} role="status">
            <span className="chat-widget-typing m4-dots">
              <span />
              <span />
              <span />
            </span>
            <span className="muted">Pensando…</span>
          </div>
        </div>
      )}
    </>
  );
}

export function ChatChips({
  prompts,
  showGuided,
  disabled,
  onPrompt,
  onGuided,
}: {
  prompts: string[];
  showGuided: boolean;
  disabled: boolean;
  onPrompt: (text: string) => void;
  onGuided: () => void;
}) {
  return (
    <div className="m4-chips" aria-label="Sugerencias">
      {prompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          className="m4-chip"
          disabled={disabled}
          onClick={() => onPrompt(prompt)}
        >
          {prompt}
        </button>
      ))}
      {showGuided && (
        <button type="button" className="m4-chip m4-chip-guided" disabled={disabled} onClick={onGuided}>
          Crear plan guiado
        </button>
      )}
    </div>
  );
}
