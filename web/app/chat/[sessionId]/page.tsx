"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Send, PanelLeft, PanelRight, Plus, Square } from "lucide-react";

import { useAuth } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AssistantMessage } from "@/components/chat/assistant-message";
import { DocumentPanel } from "@/components/chat/document-panel";
import { useChatStream } from "@/hooks/use-chat-stream";
import { cn } from "@/lib/cn";

export default function ChatSessionPage() {
  const router = useRouter();
  const { sessionId } = useParams<{ sessionId: string }>();
  const auth = useAuth();
  const [leftOpen, setLeftOpen] = React.useState(true);
  const [rightOpen, setRightOpen] = React.useState(false);
  const [input, setInput] = React.useState("");
  const { messages, streaming, error, send, stop } = useChatStream();
  const bottomRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!auth.isConfigured()) router.replace("/setup");
  }, [auth, router]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta) return;
      if (e.key === "b") {
        e.preventDefault();
        setLeftOpen((v) => !v);
      } else if (e.key === "j") {
        e.preventDefault();
        setRightOpen((v) => !v);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || streaming) return;
    if (!auth.provider || !auth.model) {
      router.push("/setup");
      return;
    }
    const text = input.trim();
    setInput("");
    await send({
      session_id: sessionId,
      message: text,
      provider: auth.provider,
      model: auth.model,
      base_url: auth.baseUrl ?? undefined,
    });
  }

  return (
    <div className="grid h-screen grid-rows-[3.5rem_1fr] bg-bg">
      <header className="flex items-center justify-between border-b border-border/60 px-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" aria-label="Toggle sessions" onClick={() => setLeftOpen((v) => !v)}>
            <PanelLeft className="h-4 w-4" />
          </Button>
          <Link href="/" className="font-semibold tracking-tight">
            <span className="inline-block h-2.5 w-2.5 -translate-y-0.5 rounded-sm bg-accent align-middle" />{" "}
            Ledgermind
          </Link>
          <Badge variant="muted" className="ml-2">
            session · {sessionId.slice(0, 8)}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          {auth.provider && (
            <Link href="/setup">
              <Badge variant="accent" className="cursor-pointer">
                {auth.provider} · {auth.model}
                {auth.keyLast4 ? ` · …${auth.keyLast4}` : ""}
              </Badge>
            </Link>
          )}
          <Button variant="ghost" size="icon" aria-label="Toggle documents" onClick={() => setRightOpen((v) => !v)}>
            <PanelRight className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="grid h-full overflow-hidden" style={panelGrid(leftOpen, rightOpen)}>
        {leftOpen && (
          <aside className="overflow-y-auto border-e border-border/60 bg-surface/40">
            <div className="p-3">
              <Button size="sm" variant="secondary" className="w-full justify-start">
                <Plus className="h-4 w-4" /> New chat
              </Button>
            </div>
            <div className="px-3 pb-3 text-xs uppercase tracking-wider text-muted">Recent</div>
            <ul className="px-2 pb-6 text-sm">
              <li className="rounded-md bg-surface2 px-3 py-2 text-ink">Current session</li>
            </ul>
          </aside>
        )}

        <main className="flex h-full flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-3xl px-6 py-8">
              {messages.length === 0 ? (
                <EmptyState />
              ) : (
                <div className="space-y-6">
                  {messages.map((m) =>
                    m.role === "user" ? (
                      <UserBubble key={m.id} content={m.content} />
                    ) : (
                      <AssistantMessage key={m.id} message={m} streaming={streaming} />
                    ),
                  )}
                </div>
              )}
              {error && !streaming && (
                <div className="mt-6 rounded-lg border border-negative/30 bg-negative/5 p-3 text-sm text-negative">
                  {error}
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </div>

          <form onSubmit={onSubmit} className="border-t border-border/60 bg-bg/60 p-4 backdrop-blur">
            <div className="mx-auto flex max-w-3xl items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    onSubmit(e);
                  }
                }}
                rows={1}
                placeholder="Ask about a financial statement…"
                className="min-h-[2.5rem] max-h-40 flex-1 resize-none rounded-md border border-border bg-surface2 px-3 py-2 text-sm text-ink placeholder:text-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60"
                disabled={streaming}
              />
              {streaming ? (
                <Button type="button" variant="secondary" onClick={stop}>
                  <Square className="h-4 w-4" />
                  Stop
                </Button>
              ) : (
                <Button type="submit" disabled={!input.trim()}>
                  <Send className="h-4 w-4" />
                  <span className="sr-only sm:not-sr-only">Send</span>
                </Button>
              )}
            </div>
            <p className="mx-auto mt-2 max-w-3xl text-xs text-muted/80">
              Cmd/Ctrl+Enter to send · Cmd/Ctrl+B sessions · Cmd/Ctrl+J docs
            </p>
          </form>
        </main>

        {rightOpen && (
          <aside className="overflow-y-auto border-s border-border/60 bg-surface/40">
            <DocumentPanel sessionId={sessionId} />
          </aside>
        )}
      </div>
    </div>
  );
}

function panelGrid(left: boolean, right: boolean): React.CSSProperties {
  const cols = [left ? "260px" : "0", "1fr", right ? "320px" : "0"]
    .filter((c) => c !== "0")
    .join(" ");
  return { gridTemplateColumns: cols };
}

function UserBubble({ content }: { content: string }) {
  return (
    <div className="flex justify-end animate-fade-in">
      <div className={cn(
        "max-w-[80%] rounded-2xl rounded-br-sm border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm",
      )}>
        {content}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mt-16 text-center">
      <Badge variant="muted">No messages yet</Badge>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight">Ask about a financial statement.</h2>
      <p className="mx-auto mt-2 max-w-md text-muted">
        Try: <em>&ldquo;What was operating margin in FY2024?&rdquo;</em> or{" "}
        <em>&ldquo;Compare revenue between Q2 2024 and Q2 2023.&rdquo;</em>
      </p>
    </div>
  );
}
