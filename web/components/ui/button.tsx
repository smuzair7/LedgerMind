"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60 disabled:cursor-not-allowed disabled:opacity-50 select-none",
  {
    variants: {
      variant: {
        primary:
          "bg-accent text-bg hover:bg-accent-hi shadow-sm",
        secondary:
          "bg-surface2 text-ink hover:bg-surface2/80 border border-border",
        ghost:
          "text-ink hover:bg-surface2/60",
        danger:
          "bg-negative/15 text-negative hover:bg-negative/25 border border-negative/30",
        link:
          "text-accent hover:text-accent-hi underline-offset-4 hover:underline px-0",
      },
      size: {
        sm: "h-8 px-3",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ className, variant, size, ...props }, ref) {
    return (
      <button
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    );
  },
);
