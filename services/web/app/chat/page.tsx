"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { ChatComposer } from "@/components/ChatComposer";
import { useChatEngine } from "@/lib/useChatEngine";

const TOKEN_KEY = "traingapp_token";

export default function Chat() {
  const router = useRouter();
  const messagesRef = useRef<HTMLDivElement>(null);
  const { messages, text, setText, busy, handleSend } = useChatEngine();

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
        <span className="chat-page-title">Asistente de entrenamiento</span>
        <span className="chat-page-header-spacer" />
      </header>

      <div className="chat-page-messages" ref={messagesRef}>
        {messages.map((message, index) => (
          <div
            key={`${index}-${message.text}`}
            className={`chat-page-bubble ${message.role}`}
          >
            {message.text}
          </div>
        ))}
        {busy && (
          <div className="chat-page-bubble assistant chat-widget-typing">
            <span />
            <span />
            <span />
          </div>
        )}
      </div>

      <form
        className="chat-page-composer"
        onSubmit={(event) => {
          event.preventDefault();
          void handleSend(text);
        }}
      >
        <ChatComposer
          placeholder="Escríbeme «recomiéndame un plan»"
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
