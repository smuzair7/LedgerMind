"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Send, FileText, PanelLeft, PanelRight, Plus } from "lucide-react";

import { useAuth } from "@/lib/auth-store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/cn";

interface DraftMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

export default function ChatSessionPage() {
  const router = useRouter();
  const { sessionId } = useParams<{ sessionId: string }>();
  const auth = useAuth();
  const [leftOpen, setLeftOpen] = React.useState(true);
  const [rightOpen, setRightOpen] = React.useState(false);
  const [input, setInput] = React.useState("");
  const [messages, setMessages] = React.useState<DraftMessage[]>([]);

  React.useEffect(() => {
    if (!auth.isConfigured()) router.replace("/setup");
  }, [auth, router]);

  // Keyboard shortcuts for pane collapse — full set lands in i18n+RTL milestone.
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

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;
    // Real streaming lands in milestone #4. For the skeleton we just echo
    // the user message into the thread so the UI is navigable.
    const user: DraftMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    const placeholder: DraftMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content:
        "Streaming wiring lands in milestone #4. Once enabled, citations will appear here before the answer, and any computed numbers will render as audited calculation cards.",
    };
    setMessages((prev) => [...prev, user, placeholder]);
    setInput("");
  }

  return (
    <div className="grid h-screen grid-rows-[3.5rem_1fr] bg-bg">
      {/* Top bar */}
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
            <Badge variant="accent">
              {auth.provider} · {auth.model}
              {auth.keyLast4 ? ` · …${auth.keyLast4}` : ""}
            </Badge>
          )}
          <Button variant="ghost" size="icon" aria-label="Toggle documents" onClick={() => setRightOpen((v) => !v)}>
            <PanelRight className="h-4 w-4" />
          </Button>
        </div>
      </header>

      <div className="grid h-full overflow-hidden" style={panelGrid(leftOpen, rightOpen)}>
        {/* Sessions pane */}
        {leftOpen && (
          <aside className="overflow-y-auto border-e border-border/60 bg-surface/40">
            <div className="p-3">
              <Button size="sm" variant="secondary" className="w-full justify-start">
                <Plus className="h-4 w-4" /> New chat
              </Button>
            </div>
            <div className="px-3 pb-3 text-xs uppercase tracking-wider text-muted">
              Recent
            </div>
            <ul className="px-2 pb-6 text-sm">
              <li
                className={cn(
                  "rounded-md px-3 py-2 text-ink",
                  "bg-surface2",
                )}
              >
                Current session
              </li>
            </ul>
          </aside>
        )}

        {/* Main */}
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
                      <AssistantBubble key={m.id} content={m.content} />
                    ),
                  )}
                </div>
              )}
            </div>
          </div>
          <form
            onSubmit={onSubmit}
            className="border-t border-border/60 bg-bg/60 p-4 backdrop-blur"
          >
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
              />
              <Button type="submit" disabled={!input.trim()}>
                <Send className="h-4 w-4" />
                <span className="sr-only sm:not-sr-only">Send</span>
              </Button>
            </div>
            <p className="mx-auto mt-2 max-w-3xl text-xs text-muted/80">
              Cmd/Ctrl+Enter to send · Cmd/Ctrl+B sessions · Cmd/Ctrl+J docs
            </p>
          </form>
        </main>

        {/* Document pane */}
        {rightOpen && (
          <aside className="overflow-y-auto border-s border-border/60 bg-surface/40 p-4">
            <div className="text-sm font-semibold">Documents</div>
            <p className="mt-1 text-xs text-muted">
              Upload + citation viewer land in milestone #5.
            </p>
            <Card className="mt-4 p-4 text-xs text-muted">
              <div className="flex items-center gap-2 text-ink">
                <FileText className="h-4 w-4 text-accent" />
                Drag PDFs here once ingestion is wired
              </div>
            </Card>
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
      <div className="max-w-[80%] rounded-2xl rounded-br-sm border border-accent/30 bg-accent/10 px-4 py-2.5 text-sm">
        {content}
      </div>
    </div>
  );
}

function AssistantBubble({ content }: { content: string }) {
  return (
    <div className="animate-fade-in space-y-2">
      <div className="text-xs uppercase tracking-wider text-muted">Ledgermind</div>
      <div className="text-pretty text-[15px] leading-relaxed">{content}</div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mt-16 text-center">
      <Badge variant="muted">No messages yet</Badge>
      <h2 className="mt-3 text-2xl font-semibold tracking-tight">
        Ask about a financial statement.
      </h2>
      <p className="mx-auto mt-2 max-w-md text-muted">
        Try: <em>&ldquo;What was operating margin in FY2024?&rdquo;</em> or{" "}
        <em>&ldquo;Compare revenue between Q2 2024 and Q2 2023.&rdquo;</em>
      </p>
    </div>
  );
}
