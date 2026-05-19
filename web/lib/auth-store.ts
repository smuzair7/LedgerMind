"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface AuthSnapshot {
  provider: string | null;
  model: string | null;
  baseUrl: string | null;
  keyLast4: string | null;
  validatedAt: number | null;
}

interface AuthStore extends AuthSnapshot {
  setSelection: (s: Partial<AuthSnapshot>) => void;
  clear: () => void;
  isConfigured: () => boolean;
}

const empty: AuthSnapshot = {
  provider: null,
  model: null,
  baseUrl: null,
  keyLast4: null,
  validatedAt: null,
};

// sessionStorage chosen deliberately: cleared on tab close. The actual API
// key lives in a separate sessionStorage slot owned by lib/api-client.ts.
export const useAuth = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...empty,
      setSelection: (s) => set((prev) => ({ ...prev, ...s })),
      clear: () => set({ ...empty }),
      isConfigured: () => {
        const s = get();
        return Boolean(s.provider && s.model && s.keyLast4 && s.validatedAt);
      },
    }),
    {
      name: "ledgermind:auth",
      storage: createJSONStorage(() =>
        typeof window === "undefined" ? (undefined as never) : window.sessionStorage,
      ),
    },
  ),
);

export function maskKey(key: string): string {
  if (key.length <= 4) return "•".repeat(key.length);
  return `${"•".repeat(Math.max(4, key.length - 4))}${key.slice(-4)}`;
}

export function last4(key: string): string {
  return key.slice(-4);
}
