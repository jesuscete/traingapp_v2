"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { ChatComposer } from "@/components/ChatComposer";
import { ChatChips, ChatThread } from "@/components/ChatThread";
import { GUIDED_PROMPT, STARTER_PROMPTS, useChatEngine } from "@/lib/useChatEngine";

const TOKEN_KEY = "traingapp_token";

export default function Chat() {
  const router = useRouter();
  const messagesRef = useRef<HTMLDivElement>(null);
  const { messages, text, setText, busy, handleSend, confirmAction, discardAction, newConversation } =
    useChatEngine();

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      router.replace("/");
    }
  }, [router]);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  function goBack() {
    if (window.history.length > 1) {
      router.back();
    } else {
      router.push("/dashboard");
    }
  }

  return (
    <div className="chat-page">
      <header className="chat-page-header">
        <button
          type="button"
          className="chat-widget-icon-btn"
          aria-label="Volver"
          onClick={goBack}
        >
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="chat-page-title">Entrenador</span>
        <button
          type="button"
          className="m4-new-chat"
          disabled={busy}
          onClick={() => void newConversation()}
        >
          Nueva conversación
        </button>
      </header>

      <div className="chat-page-messages" ref={messagesRef}>
        <ChatThread
          variant="page"
          messages={messages}
          busy={busy}
          onConfirm={(m, a) => void confirmAction(m, a)}
          onDiscard={(m, a) => void discardAction(m, a)}
        />
      </div>

      <ChatChips
        prompts={messages.length <= 1 ? STARTER_PROMPTS : []}
        showGuided
        disabled={busy}
        onPrompt={(t) => void handleSend(t)}
        onGuided={() => void handleSend(GUIDED_PROMPT, { guided: true })}
      />

      <form
        className="chat-page-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void handleSend(text);
        }}
      >
        <ChatComposer
          placeholder="Pregunta o pide algo a tu entrenador…"
          value={text}
          onChange={setText}
          onSubmit={() => void handleSend(text)}
          disabled={busy}
          hint="Enter para enviar"
        />
      </form>
    </div>
  );
}
