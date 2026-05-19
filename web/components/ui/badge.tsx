import * as React from "react";
import { cn } from "@/lib/cn";

type Variant = "default" | "accent" | "muted" | "positive" | "negative";

export function Badge({
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  const variants: Record<Variant, string> = {
    default: "border-border bg-surface2 text-ink",
    accent: "border-accent/30 bg-accent/10 text-accent-hi",
    muted: "border-border/60 bg-surface text-muted",
    positive: "border-positive/30 bg-positive/10 text-positive",
    negative: "border-negative/30 bg-negative/10 text-negative",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
