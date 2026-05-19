"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ChatMessage } from "@/hooks/use-chat-stream";
import { CitationChip } from "./citation-chip";
import { ToolCard } from "./tool-card";

interface Props {
  message: ChatMessage;
  streaming: boolean;
}

/**
 * To avoid markdown re-render thrash on every streamed token, we render the
 * in-flight content as a single <div> with whitespace-pre-wrap (one text-node
 * mutation per token). Once `done`, we swap to react-markdown.
 */
export function AssistantMessage({ message, streaming }: Props) {
  const isLive = streaming && !message.done;

  return (
    <article className="animate-fade-in space-y-3">
      <div className="text-xs uppercase tracking-wider text-muted">Ledgermind</div>

      {message.citations && message.citations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.citations.map((c, i) => (
            <CitationChip key={c.id} citation={c} index={i} />
          ))}
        </div>
      )}

      {message.tools && message.tools.length > 0 && (
        <div className="space-y-2">
          {message.tools.map((t) => (
            <ToolCard key={t.id} tool={t} />
          ))}
        </div>
      )}

      {isLive ? (
        <div className="whitespace-pre-wrap text-[15px] leading-relaxed">
          {message.content}
          <span className="ms-1 inline-block h-3.5 w-1 -translate-y-[1px] animate-pulse bg-accent align-middle" />
        </div>
      ) : (
        <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-p:my-2 prose-pre:bg-surface2 prose-pre:border prose-pre:border-border prose-code:text-accent-hi">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      )}

      {message.error && (
        <p className="text-xs text-negative">Error: {message.error}</p>
      )}

      {message.done && message.usage && (
        <p className="text-[11px] text-muted/70 tabular">
          {message.usage.firstTokenMs !== null && (
            <span>TTFT {Math.round(message.usage.firstTokenMs)} ms · </span>
          )}
          {message.usage.totalMs !== null && (
            <span>total {(message.usage.totalMs / 1000).toFixed(2)} s</span>
          )}
          {message.usage.completion_tokens !== null && (
            <span> · {message.usage.completion_tokens} tok</span>
          )}
          {message.usage.cache_read_tokens ? (
            <span> · cache hit {message.usage.cache_read_tokens.toLocaleString()} tok</span>
          ) : null}
        </p>
      )}
    </article>
  );
}
