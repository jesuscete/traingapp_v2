"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChatComposer } from "@/components/ChatComposer";
import { useChatEngine } from "@/lib/useChatEngine";

const TOKEN_KEY = "traingapp_token";

export function ChatWidget() {
  const router = useRouter();
  const pathname = usePathname();
  const messagesRef = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  const [open, setOpen] = useState(false);
  const { messages, text, setText, busy, handleSend } = useChatEngine();

  useEffect(() => {
    if (localStorage.getItem(TOKEN_KEY)) {
      setVisible(true);
    }
  }, []);

  useEffect(() => {
    if (pathname.startsWith("/chat")) setOpen(false);
  }, [pathname]);

  useEffect(() => {
    const el = messagesRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, busy]);

  if (!visible) return null;
  if (pathname.startsWith("/chat")) return null;

  return (
    <div className="chat-widget">
      {open && (
        <div className="chat-widget-panel">
          <div className="chat-widget-header">
            <span className="chat-widget-title">Asistente de entrenamiento</span>
            <div className="chat-widget-header-actions">
              <button
                type="button"
                className="chat-widget-icon-btn"
                aria-label="Pantalla completa"
                title="Pantalla completa"
                onClick={() => router.push("/chat")}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M8 3H5a2 2 0 0 0-2 2v3" />
                  <path d="M21 8V5a2 2 0 0 0-2-2h-3" />
                  <path d="M3 16v3a2 2 0 0 0 2 2h3" />
                  <path d="M16 21h3a2 2 0 0 0 2-2v-3" />
                </svg>
              </button>
              <button
                type="button"
                className="chat-widget-icon-btn"
                aria-label="Cerrar"
                title="Cerrar"
                onClick={() => setOpen(false)}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
          </div>
          <div className="chat-widget-messages" ref={messagesRef}>
            {messages.map((message, index) => (
              <div
                key={`${index}-${message.text}`}
                className={`chat-widget-bubble ${message.role}`}
              >
                {message.text}
              </div>
            ))}
            {busy && (
              <div className="chat-widget-bubble assistant chat-widget-typing">
                <span />
                <span />
                <span />
              </div>
            )}
          </div>
          <form
            className="chat-widget-composer"
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
      )}
      <button
        type="button"
        className="chat-widget-fab"
        aria-label="Abrir asistente"
        onClick={() => setOpen((prev) => !prev)}
      >
        {open ? (
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
    </div>
  );
}
