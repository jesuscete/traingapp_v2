import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { ChatMessageOut } from "@/lib/types";

export type ChatMessage = { role: "user" | "assistant"; text: string };

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const GREETING_RE =
  /\b(hola|buenas|buenos\s+d[ií]as|hey|hi|hello|saludos|qu[eé]\s+t[aá]l)\b/i;
const PLAN_HINT_RE =
  /(recomend|ay[uú]d|rutina|plan|planes|entrenamiento|entrenar|empezar|ponerme|necesit|sugerir|aconsej)/i;
const PROGRESS_RE = /\b(progreso|historial|an[aá]lisis)\b/i;

const HELP_TEXT =
  "No he entendido eso del todo. Puedo ayudarte a crear tu plan de entrenamiento: escríbeme por ejemplo «me gustaría que me recomendaras una rutina».";
const PROGRESS_TEXT =
  "Tu historial y tu progreso están en el panel Análisis de la pantalla principal.";

export function buildWelcome(userName: string | null): ChatMessage {
  const name = userName ? ` ${userName}` : "";
  return {
    role: "assistant",
    text: `Hola${name}, soy tu entrenador personal, ¿en qué puedo ayudarte?\n- Crear rutina\n- Recomiéndame un plan\n- Ver mi progreso`,
  };
}

export function useChatEngine() {
  const [token, setToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [planActive, setPlanActive] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) setToken(stored);
    let name: string | null = null;
    const rawUser = localStorage.getItem(USER_KEY);
    if (rawUser) {
      try {
        const parsed = JSON.parse(rawUser) as { name?: string };
        name = parsed.name?.trim().split(/\s+/)[0] ?? null;
      } catch {
        name = null;
      }
    }
    setUserName(name);
    setMessages([buildWelcome(name)]);
  }, []);

  const pushMessage = useCallback((message: ChatMessage) => {
    setMessages((prev) => [...prev, message]);
  }, []);

  const handleResponse = useCallback(
    (response: ChatMessageOut) => {
      if (response.mode === "plan") {
        const status = response.planStatus ?? "question";
        if (status === "done" || status === "cancelled") {
          setPlanActive(false);
          pushMessage({
            role: "assistant",
            text: response.message ?? "Entendido.",
          });
          return;
        }
        setPlanActive(true);
        pushMessage({
          role: "assistant",
          text: response.message ?? "Vamos a crear tu plan de entrenamiento.",
        });
        return;
      }
      pushMessage({ role: "assistant", text: HELP_TEXT });
    },
    [pushMessage],
  );

  const handleSend = useCallback(
    async (value: string) => {
      const trimmed = value.trim();
      if (!trimmed || busy || !token) return;
      setText("");
      pushMessage({ role: "user", text: trimmed });

      if (!planActive) {
        if (GREETING_RE.test(trimmed)) {
          pushMessage(buildWelcome(userName));
          return;
        }
        if (PROGRESS_RE.test(trimmed)) {
          pushMessage({ role: "assistant", text: PROGRESS_TEXT });
          return;
        }
        if (!PLAN_HINT_RE.test(trimmed)) {
          pushMessage({ role: "assistant", text: HELP_TEXT });
          return;
        }
      }

      setBusy(true);
      try {
        const response = await api.sendDraft(token, trimmed);
        handleResponse(response);
      } catch (err) {
        pushMessage({
          role: "assistant",
          text:
            err instanceof Error ? err.message : "Error al procesar el mensaje",
        });
      } finally {
        setBusy(false);
      }
    },
    [busy, token, planActive, userName, pushMessage, handleResponse],
  );

  return {
    messages,
    text,
    setText,
    busy,
    planActive,
    handleSend,
    token,
  };
}
