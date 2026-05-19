/**
 * Streaming chat API. Goes through the Next.js Edge proxy at
 * /api/proxy/api/chat/stream so headers (X-Provider-Key) are forwarded server
 * side and the response body is streamed through unbuffered.
 *
 * Yields typed events keyed by SSE event name.
 */

import { streamSse } from "./sse";
import { getProviderKey } from "./api-client";

export interface ChatRequestBody {
  session_id?: string;
  message: string;
  provider: string;
  model: string;
  base_url?: string;
  temperature?: number;
  tools_enabled?: boolean;
  language?: "en" | "ar" | "both";
}

export type ChatEvent =
  | { type: "citations"; citations: Citation[] }
  | { type: "token"; delta: string }
  | { type: "tool_call"; id: string; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; id: string; ok: boolean; result: unknown; audit?: unknown }
  | {
      type: "usage";
      prompt_tokens: number | null;
      completion_tokens: number | null;
      cache_read_tokens: number | null;
      cache_write_tokens: number | null;
    }
  | { type: "done" }
  | { type: "error"; code: string; message: string };

export interface Citation {
  id: string;
  doc_id: string;
  doc_name: string;
  page: number;
  bbox?: [number, number, number, number] | null;
  snippet?: string | null;
}

export async function* streamChat(
  body: ChatRequestBody,
  signal?: AbortSignal,
): AsyncGenerator<ChatEvent, void, void> {
  const key = getProviderKey();
  if (!key) {
    yield {
      type: "error",
      code: "no_key",
      message: "Provider key missing — visit /setup.",
    };
    return;
  }

  const headers = new Headers({
    "Content-Type": "application/json",
    "X-Provider-Key": key,
    Accept: "text/event-stream",
  });

  // Same-origin proxy to keep CORS off the critical path and stream unbuffered.
  for await (const ev of streamSse("/api/proxy/api/chat/stream", {
    headers,
    body: JSON.stringify(body),
    signal,
  })) {
    const parsed = parseEvent(ev.event, ev.data);
    if (parsed) yield parsed;
  }
}

function parseEvent(name: string, data: string): ChatEvent | null {
  try {
    const obj = data ? JSON.parse(data) : {};
    switch (name) {
      case "citations":
        return { type: "citations", citations: obj.citations ?? [] };
      case "token":
        return { type: "token", delta: obj.delta ?? "" };
      case "tool_call":
        return {
          type: "tool_call",
          id: obj.id,
          name: obj.name,
          args: obj.args ?? {},
        };
      case "tool_result":
        return {
          type: "tool_result",
          id: obj.id,
          ok: obj.ok,
          result: obj.result,
          audit: obj.audit,
        };
      case "usage":
        return {
          type: "usage",
          prompt_tokens: obj.prompt_tokens ?? null,
          completion_tokens: obj.completion_tokens ?? null,
          cache_read_tokens: obj.cache_read_tokens ?? null,
          cache_write_tokens: obj.cache_write_tokens ?? null,
        };
      case "done":
        return { type: "done" };
      case "error":
        return { type: "error", code: obj.code ?? "unknown", message: obj.message ?? "" };
      default:
        return null;
    }
  } catch {
    return null;
  }
}
