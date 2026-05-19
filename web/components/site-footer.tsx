import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 py-10 text-sm text-muted">
      <div className="container-wide flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <p>
          Ledgermind · MIT · BYO-key, browser-only — your provider key never touches our disk.
        </p>
        <div className="flex items-center gap-4">
          <Link href="/architecture" className="hover:text-ink">
            Architecture
          </Link>
          <a
            href="https://github.com/smuzair7/LedgerMind"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
