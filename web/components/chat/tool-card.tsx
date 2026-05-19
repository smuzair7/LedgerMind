"use client";

import * as React from "react";
import { ChevronDown, Calculator, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ToolEvent } from "@/hooks/use-chat-stream";

export function ToolCard({ tool }: { tool: ToolEvent }) {
  const [open, setOpen] = React.useState(false);
  const pending = tool.ok === undefined;

  return (
    <div
      className={cn(
        "rounded-xl border bg-surface/80 p-4 text-sm",
        pending
          ? "border-border"
          : tool.ok
            ? "border-accent/30 bg-accent/5"
            : "border-negative/30 bg-negative/5",
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {pending ? (
            <Loader2 className="h-4 w-4 animate-spin text-accent" />
          ) : (
            <Calculator className="h-4 w-4 text-accent" />
          )}
          <span className="font-medium">{prettyName(tool.name)}</span>
        </div>
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1 text-xs text-muted hover:text-ink"
        >
          {open ? "Hide working" : "Show working"}
          <ChevronDown
            className={cn("h-3 w-3 transition-transform", open && "rotate-180")}
          />
        </button>
      </div>

      {!pending && renderResult(tool)}

      {open && (
        <pre className="mt-3 overflow-x-auto rounded-md bg-surface2 p-3 font-mono text-[11px] leading-relaxed text-muted">
{JSON.stringify({ args: tool.args, result: tool.result, audit: tool.audit }, null, 2)}
        </pre>
      )}
    </div>
  );
}

function renderResult(tool: ToolEvent) {
  if (tool.ok === false) {
    return (
      <p className="mt-2 text-xs text-negative">
        Tool failed: {String((tool.result as { error?: string })?.error ?? "unknown")}
      </p>
    );
  }
  const result = tool.result as Record<string, unknown> | null;
  if (!result || typeof result !== "object") return null;
  const value = result["value"];
  const formula = result["formula"];
  return (
    <div className="mt-3 space-y-2">
      {formula !== undefined && (
        <p className="font-mono text-xs text-muted">{String(formula)}</p>
      )}
      {value !== undefined && (
        <p className="text-3xl font-semibold tabular text-accent-hi">
          {formatValue(value)}
        </p>
      )}
    </div>
  );
}

function prettyName(name: string): string {
  return name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(v: unknown): string {
  if (typeof v === "number") {
    if (Math.abs(v) < 1 && v !== 0) return (v * 100).toFixed(2) + "%";
    return v.toLocaleString();
  }
  return String(v);
}
