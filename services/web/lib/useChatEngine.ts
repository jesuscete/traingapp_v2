import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { ApiError, api } from "@/lib/api";
import {
  getChatState,
  getServerChatState,
  hydrateChat,
  newMessageId,
  patchChatAction,
  pushChatMessage,
  resetChat,
  setPlanActive,
  subscribeChat,
  type ChatMessage,
} from "@/lib/chatStore";
import { summarizeMetrics } from "@/lib/metrics";
import { translateDiscipline } from "@/lib/labels";
import type { ChatMessageOut, WorkoutDraft } from "@/lib/types";

export type { ChatActionState, ChatMessage } from "@/lib/chatStore";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const GREETING_RE =
  /^\s*(hola|buenas|buenos\s+d[ií]as|hey|hi|hello|saludos|qu[eé]\s+t[aá]l)\W*$/i;
/** Peticiones de crear/recomendar un plan o rutina: flujo guiado antiguo. */
const GUIDED_RE =
  /(recomi[eé]nd\w*|recomend\w*|cre[ae]\w*|dise[nñ]\w*|arm[ae]\w*|h[aá]zme|necesito)\s.*\b(plan|planes|rutina)\b/i;

export const GUIDED_PROMPT = "Quiero que me recomiendes un plan de entrenamiento";

export const STARTER_PROMPTS = [
  "¿Cómo voy de fatiga?",
  "¿Qué me falta para el boxeo?",
  "Registra: 6 rounds de saco y 20 min de comba",
  "Sustituye el press banca por algo con mancuernas",
];

export const TOOL_LABELS: Record<string, string> = {
  ver_fatiga: "fatiga",
  explicar_fatiga: "causas de fatiga",
  sesiones_recientes: "sesiones recientes",
  analisis_deporte: "análisis del deporte",
  ver_rutina: "rutina",
  buscar_ejercicios: "catálogo",
  alternativas_ejercicio: "alternativas",
  registrar_entreno: "registro de entreno",
  registrar_comida: "registro de comida",
  ver_nutricion: "tu nutrición de hoy",
  perfil_deporte: "perfil de tu deporte",
  sustituir_en_rutina: "sustitución",
  anadir_a_rutina: "añadir a rutina",
};

export function describeDraft(draft: WorkoutDraft): string {
  const lines = [
    `Borrador: ${translateDiscipline(draft.discipline)}${
      draft.durationMinutes != null ? ` · ${draft.durationMinutes} min` : ""
    }`,
  ];
  const metrics = summarizeMetrics(draft.metrics);
  if (metrics) lines.push(metrics);
  if (draft.unresolved.length > 0) lines.push(`Sin resolver: ${draft.unresolved.join(", ")}`);
  return lines.join("\n");
}

export function buildWelcome(userName: string | null): ChatMessage {
  const name = userName ? ` ${userName}` : "";
  return {
    id: newMessageId(),
    role: "assistant",
    text: `Hola${name}, soy tu entrenador. Puedo revisar tu fatiga, analizar tu preparación para el boxeo, registrar entrenos y ajustar tu rutina. ¿Qué necesitas?`,
  };
}

function readUserName(): string | null {
  try {
    const rawUser = localStorage.getItem(USER_KEY);
    if (!rawUser) return null;
    const parsed = JSON.parse(rawUser) as { name?: string };
    return parsed.name?.trim().split(/\s+/)[0] ?? null;
  } catch {
    return null;
  }
}

function errorText(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

function assistant(text: string, extra: Partial<ChatMessage> = {}): ChatMessage {
  return { id: newMessageId(), role: "assistant", text, ...extra };
}

export function useChatEngine() {
  const [token, setToken] = useState<string | null>(null);
  const [userName, setUserName] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const { messages, planActive } = useSyncExternalStore(
    subscribeChat,
    getChatState,
    getServerChatState,
  );

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(TOKEN_KEY);
    } catch {
      stored = null;
    }
    if (stored) setToken(stored);
    const name = readUserName();
    setUserName(name);
    hydrateChat(() => buildWelcome(name));
  }, []);

  const handleGuidedResponse = useCallback((response: ChatMessageOut) => {
    if (response.mode === "plan") {
      const status = response.planStatus ?? "question";
      if (status === "done" || status === "cancelled") {
        setPlanActive(false);
        pushChatMessage(assistant(response.message ?? "Entendido."));
        return;
      }
      setPlanActive(true);
      pushChatMessage(assistant(response.message ?? "Vamos a crear tu plan de entrenamiento."));
      return;
    }
    if (response.mode === "confirm" && response.draft && response.requestId) {
      pushChatMessage(
        assistant("¿Guardo este entreno?", {
          actions: [
            {
              id: response.requestId,
              type: "save_workout",
              summary: describeDraft(response.draft),
              requestId: response.requestId,
              status: "pending",
            },
          ],
        }),
      );
      return;
    }
    pushChatMessage(
      assistant(
        response.message ??
          "No he entendido eso. Prueba a preguntarme otra cosa o pulsa «Crear plan guiado».",
      ),
    );
  }, []);

  const handleSend = useCallback(
    async (value: string, options: { guided?: boolean } = {}) => {
      const trimmed = value.trim();
      if (!trimmed || busy || !token) return;
      setText("");
      pushChatMessage({ id: newMessageId(), role: "user", text: trimmed });

      const guided = options.guided === true || planActive || GUIDED_RE.test(trimmed);
      if (!guided && GREETING_RE.test(trimmed)) {
        pushChatMessage(buildWelcome(userName));
        return;
      }

      setBusy(true);
      try {
        if (guided) {
          handleGuidedResponse(await api.sendDraft(token, trimmed));
        } else {
          const reply = await api.sendAgentMessage(token, trimmed);
          pushChatMessage(
            assistant(reply.reply, {
              actions: reply.actions.map((action) => ({ ...action, status: "pending" as const })),
              tools: reply.toolsUsed,
            }),
          );
        }
      } catch (err) {
        pushChatMessage(
          assistant(`No he podido responder: ${errorText(err, "error al procesar el mensaje")}`),
        );
      } finally {
        setBusy(false);
      }
    },
    [busy, token, planActive, userName, handleGuidedResponse],
  );

  const confirmAction = useCallback(
    async (messageId: string, actionId: string) => {
      if (!token) return;
      const action = getChatState()
        .messages.find((m) => m.id === messageId)
        ?.actions?.find((a) => a.id === actionId);
      if (!action || action.status === "busy" || action.status === "done") return;
      patchChatAction(messageId, actionId, { status: "busy", error: undefined });
      try {
        if (action.type === "save_workout") {
          if (!action.requestId) throw new Error("Falta el identificador del borrador");
          const saved = await api.confirmDraft(token, { requestId: action.requestId });
          patchChatAction(messageId, actionId, {
            status: "done",
            result: "Entreno guardado.",
            sessionId: saved.id,
          });
        } else {
          const result = await api.confirmAgentAction(token, actionId);
          patchChatAction(messageId, actionId, { status: "done", result: result.message });
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          patchChatAction(messageId, actionId, {
            status: "expired",
            error: "Esta acción ha caducado. Pídemela de nuevo.",
          });
        } else if (err instanceof ApiError && err.status === 409) {
          patchChatAction(messageId, actionId, { status: "failed", error: err.message });
        } else {
          patchChatAction(messageId, actionId, {
            status: "pending",
            error: errorText(err, "No se pudo confirmar la acción"),
          });
        }
      }
    },
    [token],
  );

  const discardAction = useCallback(
    async (messageId: string, actionId: string) => {
      if (!token) return;
      const action = getChatState()
        .messages.find((m) => m.id === messageId)
        ?.actions?.find((a) => a.id === actionId);
      if (!action || action.status === "busy" || action.status === "done") return;
      patchChatAction(messageId, actionId, { status: "busy", error: undefined });
      try {
        if (action.type === "save_workout") {
          if (action.requestId) await api.cancelDraft(token, action.requestId);
        } else {
          await api.discardAgentAction(token, actionId);
        }
        patchChatAction(messageId, actionId, { status: "discarded" });
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          patchChatAction(messageId, actionId, { status: "discarded" });
        } else {
          patchChatAction(messageId, actionId, {
            status: "pending",
            error: errorText(err, "No se pudo descartar la acción"),
          });
        }
      }
    },
    [token],
  );

  const newConversation = useCallback(async () => {
    if (!token || busy) return;
    setBusy(true);
    try {
      await api.resetAgentConversation(token);
      resetChat(buildWelcome(userName));
      setText("");
    } catch (err) {
      pushChatMessage(
        assistant(`No se pudo reiniciar la conversación: ${errorText(err, "error desconocido")}`),
      );
    } finally {
      setBusy(false);
    }
  }, [token, busy, userName]);

  return {
    messages,
    text,
    setText,
    busy,
    planActive,
    handleSend,
    confirmAction,
    discardAction,
    newConversation,
    token,
  };
}
