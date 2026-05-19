"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/cn";
import type { ProviderInfo } from "@/lib/providers";

interface Props {
  providers: ProviderInfo[];
  selected: string | null;
  onSelect: (id: string) => void;
}

export function ProviderGrid({ providers, selected, onSelect }: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {providers.map((p) => {
        const active = p.id === selected;
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelect(p.id)}
            className={cn(
              "group relative flex flex-col gap-2 rounded-xl border bg-surface/70 p-4 text-left transition-colors",
              active
                ? "border-accent bg-accent/5"
                : "border-border hover:border-accent/40 hover:bg-surface2/50",
            )}
            aria-pressed={active}
          >
            <div className="flex items-start justify-between">
              <div className="text-base font-semibold">{p.label}</div>
              {active && (
                <span className="grid h-5 w-5 place-items-center rounded-full bg-accent text-bg">
                  <Check className="h-3 w-3" />
                </span>
              )}
            </div>
            {p.description && (
              <p className="text-sm text-muted">{p.description}</p>
            )}
            {p.key_url && (
              <a
                href={p.key_url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 text-xs text-accent hover:text-accent-hi"
                onClick={(e) => e.stopPropagation()}
              >
                Get a key ↗
              </a>
            )}
          </button>
        );
      })}
    </div>
  );
}
