/**
 * Minimal SSE reader for fetch-based streams. The browser EventSource API
 * cannot set custom headers (no way to attach X-Provider-Key), so we use the
 * fetch + ReadableStream pattern instead.
 *
 * Frame format:
 *   event: <name>\n
 *   data: <json>\n
 *   \n
 *
 * Multi-data frames are concatenated with `\n` per the spec; we don't emit
 * those, so the parser keeps the single-line case fast.
 */

export interface SseEvent {
  event: string;
  data: string;
}

export interface StreamOptions {
  signal?: AbortSignal;
  headers?: HeadersInit;
  body?: BodyInit;
}

export async function* streamSse(
  url: string,
  init: StreamOptions = {},
): AsyncGenerator<SseEvent, void, void> {
  const res = await fetch(url, {
    method: "POST",
    headers: init.headers,
    body: init.body,
    signal: init.signal,
  });

  if (!res.ok || !res.body) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {}
    throw new Error(`stream failed ${res.status}: ${detail || res.statusText}`);
  }

  const decoder = new TextDecoder();
  const reader = res.body.getReader();

  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let sep: number;
      // Frames are separated by a blank line ("\n\n").
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const parsed = parseFrame(frame);
        if (parsed) yield parsed;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(frame: string): SseEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const rawLine of frame.split("\n")) {
    const line = rawLine.trimEnd();
    if (!line || line.startsWith(":")) continue;
    if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
