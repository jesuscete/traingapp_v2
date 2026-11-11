"use client";

import Link from "next/link";

import type { ChatActionState, ChatMessage } from "@/lib/chatStore";
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
      <p className="m4-action-summary">{action.summary}</p>
      {open && (
        <div className="m4-action-btns">
          <button
            type="button"
            disabled={action.status === "busy"}
            onClick={() => onConfirm(messageId, action.id)}
          >
            {action.status === "busy" ? "Procesando…" : "Confirmar"}
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

export function ChatThread({ variant, messages, busy, onConfirm, onDiscard }: Props) {
  const bubble = `chat-${variant}-bubble`;
  return (
    <>
      {messages.map((message) => {
        const tools = toolSummary(message.tools);
        return (
          <div key={message.id} className={`m4-msg ${message.role}`}>
            <div className={`${bubble} ${message.role}`}>{message.text}</div>
            {message.actions?.map((action) => (
              <ActionCard
                key={action.id}
                action={action}
                messageId={message.id}
                onConfirm={onConfirm}
                onDiscard={onDiscard}
              />
            ))}
            {tools && <span className="muted m4-tools">{tools}</span>}
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
