"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input({ className, type, ...props }, ref) {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          "h-10 w-full rounded-md border border-border bg-surface2 px-3 text-sm text-ink",
          "placeholder:text-muted/70",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60",
          "disabled:cursor-not-allowed disabled:opacity-50",
          type === "password" && "font-mono tracking-wider",
          className,
        )}
        {...props}
      />
    );
  },
);
