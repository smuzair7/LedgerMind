"use client";

import * as React from "react";
import {
  streamChat,
  type ChatEvent,
  type ChatRequestBody,
  type Citation,
} from "@/lib/chat-api";

export interface UsageInfo {
  prompt_tokens: number | null;
  completion_tokens: number | null;
  cache_read_tokens: number | null;
  cache_write_tokens: number | null;
  firstTokenMs: number | null;
  totalMs: number | null;
}

export interface ToolEvent {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
  audit?: unknown;
  ok?: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  tools?: ToolEvent[];
  usage?: UsageInfo;
  error?: string;
  done?: boolean;
}

interface State {
  messages: ChatMessage[];
  streaming: boolean;
  error: string | null;
}

interface Action {
  type:
    | "user"
    | "assistant_start"
    | "citations"
    | "token"
    | "tool_call"
    | "tool_result"
    | "usage"
    | "done"
    | "error"
    | "abort";
  payload?: any;
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "user": {
      const m: ChatMessage = {
        id: action.payload.id,
        role: "user",
        content: action.payload.content,
      };
      return { ...state, messages: [...state.messages, m] };
    }
    case "assistant_start": {
      const m: ChatMessage = {
        id: action.payload.id,
        role: "assistant",
        content: "",
        citations: [],
        tools: [],
        usage: undefined,
      };
      return { ...state, messages: [...state.messages, m], streaming: true, error: null };
    }
    case "citations": {
      return patchLast(state, (m) => ({ ...m, citations: action.payload as Citation[] }));
    }
    case "token": {
      return patchLast(state, (m) => ({ ...m, content: m.content + action.payload }));
    }
    case "tool_call": {
      const tool: ToolEvent = action.payload;
      return patchLast(state, (m) => ({ ...m, tools: [...(m.tools ?? []), tool] }));
    }
    case "tool_result": {
      const { id, ok, result, audit } = action.payload;
      return patchLast(state, (m) => ({
        ...m,
        tools: (m.tools ?? []).map((t) =>
          t.id === id ? { ...t, ok, result, audit } : t,
        ),
      }));
    }
    case "usage": {
      const u = action.payload as UsageInfo;
      return patchLast(state, (m) => ({ ...m, usage: { ...(m.usage ?? defaultUsage), ...u } }));
    }
    case "done": {
      return {
        ...state,
        streaming: false,
        messages: state.messages.map((m, i, arr) =>
          i === arr.length - 1 ? { ...m, done: true } : m,
        ),
      };
    }
    case "error": {
      return {
        ...state,
        streaming: false,
        error: action.payload,
        messages: state.messages.map((m, i, arr) =>
          i === arr.length - 1 ? { ...m, error: action.payload, done: true } : m,
        ),
      };
    }
    case "abort": {
      return { ...state, streaming: false };
    }
    default:
      return state;
  }
}

const defaultUsage: UsageInfo = {
  prompt_tokens: null,
  completion_tokens: null,
  cache_read_tokens: null,
  cache_write_tokens: null,
  firstTokenMs: null,
  totalMs: null,
};

function patchLast(state: State, fn: (m: ChatMessage) => ChatMessage): State {
  if (state.messages.length === 0) return state;
  const next = state.messages.slice();
  const i = next.length - 1;
  next[i] = fn(next[i]);
  return { ...state, messages: next };
}

export function useChatStream() {
  const [state, dispatch] = React.useReducer(reducer, {
    messages: [],
    streaming: false,
    error: null,
  });
  const abortRef = React.useRef<AbortController | null>(null);

  const send = React.useCallback(async (body: ChatRequestBody) => {
    if (state.streaming) return;
    const controller = new AbortController();
    abortRef.current = controller;

    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    dispatch({ type: "user", payload: { id: userId, content: body.message } });
    dispatch({ type: "assistant_start", payload: { id: assistantId } });

    const start = performance.now();
    let firstTokenAt: number | null = null;

    try {
      for await (const ev of streamChat(body, controller.signal)) {
        dispatchEvent(dispatch, ev);
        if (ev.type === "token" && firstTokenAt === null) {
          firstTokenAt = performance.now();
          dispatch({
            type: "usage",
            payload: {
              ...defaultUsage,
              firstTokenMs: firstTokenAt - start,
            },
          });
        }
        if (ev.type === "done") {
          dispatch({
            type: "usage",
            payload: {
              ...defaultUsage,
              firstTokenMs: firstTokenAt ? firstTokenAt - start : null,
              totalMs: performance.now() - start,
            },
          });
        }
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") {
        dispatch({ type: "abort" });
      } else {
        dispatch({ type: "error", payload: String(e) });
      }
    } finally {
      abortRef.current = null;
    }
  }, [state.streaming]);

  const stop = React.useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { ...state, send, stop };
}

function dispatchEvent(dispatch: React.Dispatch<Action>, ev: ChatEvent) {
  switch (ev.type) {
    case "citations":
      dispatch({ type: "citations", payload: ev.citations });
      break;
    case "token":
      dispatch({ type: "token", payload: ev.delta });
      break;
    case "tool_call":
      dispatch({
        type: "tool_call",
        payload: { id: ev.id, name: ev.name, args: ev.args },
      });
      break;
    case "tool_result":
      dispatch({
        type: "tool_result",
        payload: { id: ev.id, ok: ev.ok, result: ev.result, audit: ev.audit },
      });
      break;
    case "usage":
      dispatch({
        type: "usage",
        payload: {
          prompt_tokens: ev.prompt_tokens,
          completion_tokens: ev.completion_tokens,
          cache_read_tokens: ev.cache_read_tokens,
          cache_write_tokens: ev.cache_write_tokens,
          firstTokenMs: null,
          totalMs: null,
        },
      });
      break;
    case "done":
      dispatch({ type: "done" });
      break;
    case "error":
      dispatch({ type: "error", payload: ev.message || ev.code });
      break;
  }
}
