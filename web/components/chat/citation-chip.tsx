import type { Citation } from "@/lib/chat-api";
import { cn } from "@/lib/cn";

export function CitationChip({
  citation,
  index,
  onClick,
}: {
  citation: Citation;
  index: number;
  onClick?: (c: Citation) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick?.(citation)}
      className={cn(
        "inline-flex items-center gap-1 rounded-full border border-border bg-surface2 px-2 py-0.5 text-xs text-muted",
        "hover:border-accent/40 hover:text-ink",
      )}
      title={`${citation.doc_name} · p. ${citation.page}`}
    >
      <sup className="text-[10px] text-accent">[{index + 1}]</sup>
      <span className="max-w-[18ch] truncate">{citation.doc_name}</span>
      <span className="text-[10px] text-muted/80">p.{citation.page}</span>
    </button>
  );
}
