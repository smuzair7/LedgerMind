"use client";

import Link from "next/link";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "./theme-provider";
import { Button } from "./ui/button";

export function SiteHeader() {
  const { theme, toggle } = useTheme();
  return (
    <header className="sticky top-0 z-30 border-b border-border/60 bg-bg/70 backdrop-blur">
      <div className="container-wide flex h-14 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="inline-block h-2.5 w-2.5 rounded-sm bg-accent" />
          Ledgermind
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            href="/architecture"
            className="rounded-md px-3 py-1.5 text-muted hover:bg-surface2 hover:text-ink"
          >
            Architecture
          </Link>
          <a
            href="https://github.com/smuzair7/LedgerMind"
            target="_blank"
            rel="noreferrer"
            className="rounded-md px-3 py-1.5 text-muted hover:bg-surface2 hover:text-ink"
          >
            GitHub
          </a>
          <Button
            variant="ghost"
            size="icon"
            aria-label="Toggle theme"
            onClick={toggle}
            className="ml-1"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
          <Link href="/setup">
            <Button variant="primary" size="sm" className="ml-2">
              Try with your key
            </Button>
          </Link>
        </nav>
      </div>
    </header>
  );
}
