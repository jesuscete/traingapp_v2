import type { AgentAction, ChatCard } from "@/lib/types";

export type ChatActionStatus = "pending" | "busy" | "done" | "discarded" | "expired" | "failed";

export type ChatActionState = AgentAction & {
  status: ChatActionStatus;
  result?: string;
  sessionId?: string;
  error?: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  actions?: ChatActionState[];
  tools?: string[];
  /** Respuesta estructurada (rutina, fatiga, ejercicios…) pintada sin IA. */
  cards?: ChatCard[];
  /** "rules" = respondido sin IA por el router del servidor. */
  source?: "llm" | "fallback" | "rules";
};

export type ChatState = { messages: ChatMessage[]; planActive: boolean };

const STORAGE_KEY = "traingapp_chat_v2";

const EMPTY: ChatState = { messages: [], planActive: false };

let state: ChatState = EMPTY;
let hydrated = false;
const listeners = new Set<() => void>();

let counter = 0;
export function newMessageId(): string {
  counter += 1;
  return `${Date.now().toString(36)}-${counter}`;
}

function persist(): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // modo privado o cuota: el estado en memoria basta
  }
}

function emit(): void {
  for (const listener of listeners) listener();
}

function readStored(): ChatState | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ChatState>;
    if (!Array.isArray(parsed.messages)) return null;
    const messages = parsed.messages.map((message) => ({
      ...message,
      actions: message.actions?.map((action) =>
        action.status === "busy" ? { ...action, status: "pending" as const } : action,
      ),
    }));
    return { messages, planActive: parsed.planActive === true };
  } catch {
    return null;
  }
}

/** Carga los mensajes guardados (una vez); si no hay, inicia con `welcome`. */
export function hydrateChat(welcome: () => ChatMessage): void {
  if (hydrated) return;
  hydrated = true;
  const stored = readStored();
  state = stored && stored.messages.length > 0 ? stored : { messages: [welcome()], planActive: false };
  emit();
}

export function subscribeChat(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getChatState(): ChatState {
  return state;
}

export function getServerChatState(): ChatState {
  return EMPTY;
}

export function pushChatMessage(message: ChatMessage): void {
  state = { ...state, messages: [...state.messages, message] };
  persist();
  emit();
}

export function patchChatAction(
  messageId: string,
  actionId: string,
  patch: Partial<ChatActionState>,
): void {
  state = {
    ...state,
    messages: state.messages.map((message) =>
      message.id === messageId
        ? {
            ...message,
            actions: message.actions?.map((action) =>
              action.id === actionId ? { ...action, ...patch } : action,
            ),
          }
        : message,
    ),
  };
  persist();
  emit();
}

export function setPlanActive(planActive: boolean): void {
  if (state.planActive === planActive) return;
  state = { ...state, planActive };
  persist();
  emit();
}

export function resetChat(welcome: ChatMessage): void {
  state = { messages: [welcome], planActive: false };
  persist();
  emit();
}
