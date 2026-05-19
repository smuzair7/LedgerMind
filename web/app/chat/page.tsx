"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { apiFetch } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-store";
import { Spinner } from "@/components/ui/spinner";

interface SessionInfo {
  id: string;
  name: string;
  doc_count: number;
  created_at: string;
}

export default function ChatIndexPage() {
  const router = useRouter();
  const isConfigured = useAuth((s) => s.isConfigured());

  React.useEffect(() => {
    if (!isConfigured) {
      router.replace("/setup");
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const list = await apiFetch<SessionInfo[]>("/api/sessions");
        if (cancelled) return;
        const target = list[0]
          ? list[0]
          : await apiFetch<SessionInfo>("/api/sessions", {
              method: "POST",
              body: JSON.stringify({ name: "New chat" }),
            });
        router.replace(`/chat/${target.id}`);
      } catch {
        const target = await apiFetch<SessionInfo>("/api/sessions", {
          method: "POST",
          body: JSON.stringify({ name: "New chat" }),
        });
        if (!cancelled) router.replace(`/chat/${target.id}`);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isConfigured, router]);

  return (
    <div className="grid h-screen place-items-center text-muted">
      <span className="inline-flex items-center gap-2 text-sm">
        <Spinner className="text-accent" /> Opening a session…
      </span>
    </div>
  );
}
