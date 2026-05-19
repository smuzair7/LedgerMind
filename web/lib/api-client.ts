/**
 * API client. All backend calls go through this. Provider keys are injected
 * from sessionStorage by `withProviderKey`; we NEVER read them from
 * localStorage or any other persistent surface unless the user opts in.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const KEY_STORAGE = "ledgermind:provider-key";

export function setProviderKey(key: string): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(KEY_STORAGE, key);
}

export function getProviderKey(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(KEY_STORAGE);
}

export function clearProviderKey(): void {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(KEY_STORAGE);
}

export function buildHeaders(extra?: HeadersInit): Headers {
  const h = new Headers(extra);
  const key = getProviderKey();
  if (key) h.set("X-Provider-Key", key);
  if (!h.has("Content-Type")) h.set("Content-Type", "application/json");
  return h;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: buildHeaders(init.headers),
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = j.detail ?? JSON.stringify(j);
    } catch {
      detail = await res.text();
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}
