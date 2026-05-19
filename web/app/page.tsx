import Link from "next/link";
import {
  ArrowRight,
  Quote,
  Calculator,
  Languages,
  ShieldCheck,
  Zap,
  GitBranch,
} from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/card";

const features = [
  {
    icon: Quote,
    title: "Cited every claim",
    body: "Every retrieved chunk returns with a doc, page, and bounding box. Citations appear in the stream before the first generated token.",
  },
  {
    icon: Calculator,
    title: "Computes, doesn't guess",
    body: "Numbers are produced by deterministic tool calls (compute_ratio, compute_yoy, …) over a structured fact store — then audited inline.",
  },
  {
    icon: Languages,
    title: "Bilingual by design",
    body: "Arabic and English are indexed natively via bge-m3 — no translation hop. RTL UI flips on language switch.",
  },
  {
    icon: ShieldCheck,
    title: "Your key, your tab",
    body: "BYO key from any major provider. Stored in browser sessionStorage, forwarded per-request, scrubbed from logs, never persisted on our disk.",
  },
  {
    icon: Zap,
    title: "Streaming-first",
    body: "Server-sent events with a tagged taxonomy. First citations and tool-call cards reach the UI before the answer finishes generating.",
  },
  {
    icon: GitBranch,
    title: "Seven providers",
    body: "OpenAI, Anthropic, Google, Mistral, Cohere, Groq, plus any OpenAI-compatible endpoint (OpenRouter, Together, vLLM, llama.cpp).",
  },
];

const stack = [
  "Next.js 15",
  "React 19",
  "FastAPI",
  "Qdrant",
  "bge-m3",
  "Docling",
  "DuckDB",
  "arq",
  "Tailwind",
  "shadcn/ui",
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-grid opacity-40" aria-hidden />
        <div className="container-wide relative grid items-center gap-12 py-24 lg:grid-cols-[1.1fr_1fr] lg:py-32">
          <div className="space-y-7 animate-fade-in">
            <Badge variant="accent">Open source · MIT</Badge>
            <h1 className="text-balance text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
              Read financial statements
              <br />
              with a model that{" "}
              <span className="text-accent">shows its work</span>.
            </h1>
            <p className="max-w-xl text-pretty text-lg text-muted">
              Upload any annual report — in English or Arabic. Ask anything. Get an
              answer where every claim is cited to a page and every number is{" "}
              <em>computed</em> by a sandboxed tool call, not hallucinated by the
              model.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Link href="/setup">
                <Button size="lg" variant="primary">
                  Try with your key
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/architecture">
                <Button size="lg" variant="secondary">
                  View architecture
                </Button>
              </Link>
            </div>
            <p className="text-xs text-muted/80">
              Bring an OpenAI, Anthropic, Google, Mistral, Cohere, Groq, or
              OpenAI-compatible key. Stored in your tab. Never on our disk.
            </p>
          </div>

          {/* Mock terminal */}
          <div className="rounded-xl border border-border/70 bg-surface/70 p-5 shadow-2xl shadow-black/40 backdrop-blur-sm">
            <div className="mb-4 flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-full bg-negative/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-accent/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-positive/70" />
              <span className="ml-2 text-xs text-muted">ledgermind · chat</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex gap-2">
                <span className="text-muted">›</span>
                <span>What was gross margin in FY2024?</span>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <Badge variant="muted">[¹]</Badge>
                <Badge variant="muted">[²]</Badge>
                <Badge variant="muted">[³]</Badge>
                <span className="text-muted">citations attached before generation</span>
              </div>
              <div className="rounded-lg border border-accent/30 bg-accent/5 p-3">
                <p className="text-xs uppercase tracking-wider text-accent-hi">
                  Gross Margin · FY2024
                </p>
                <p className="mt-2 font-mono text-xs text-muted">
                  (Revenue − COGS) / Revenue
                </p>
                <p className="mt-3 text-2xl font-semibold tabular text-accent-hi">
                  45.0%
                </p>
                <p className="mt-2 text-xs text-muted">
                  Revenue&nbsp;1,234,567&nbsp;·&nbsp;COGS&nbsp;678,900&nbsp;·&nbsp;p.&nbsp;14
                </p>
              </div>
              <p className="text-xs text-muted">
                TTFT 412 ms · total 3.1 s · cache hit 1,840 tok
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Why this isn't a toy RAG */}
      <section className="border-t border-border/60 py-20">
        <div className="container-wide">
          <div className="mb-12 max-w-2xl">
            <Badge variant="muted">Why this isn't a toy RAG</Badge>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              The boring parts done well.
            </h2>
            <p className="mt-3 text-muted">
              Most chat-with-PDF demos stop at <code>PyPDF2.extract_text</code> + top-K
              cosine. Ledgermind treats the boring parts — parsing, retrieval, math,
              streaming — as the actual product.
            </p>
          </div>
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ icon: Icon, title, body }) => (
              <Card key={title} className="transition-colors hover:border-accent/40">
                <CardHeader className="flex flex-row items-center gap-3 pb-2">
                  <span className="grid h-9 w-9 place-items-center rounded-md bg-accent/10 text-accent">
                    <Icon className="h-4 w-4" />
                  </span>
                  <CardTitle>{title}</CardTitle>
                </CardHeader>
                <CardBody>{body}</CardBody>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture peek */}
      <section className="border-t border-border/60 bg-surface/30 py-20">
        <div className="container-wide grid items-center gap-12 lg:grid-cols-2">
          <div>
            <Badge variant="muted">Architecture</Badge>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Hybrid retrieval. Sandboxed math.
            </h2>
            <p className="mt-4 text-muted">
              Docling parses tables with cell grids and bboxes. <code>bge-m3</code>{" "}
              indexes Arabic and English in one model. Qdrant runs hybrid dense +
              sparse with RRF fusion. A reranker then trims to 6. Calculations are
              named tool calls executed in an AST-whitelisted sandbox — every number
              cites its source and its formula.
            </p>
            <Link
              href="/architecture"
              className="mt-5 inline-flex items-center gap-2 text-accent hover:text-accent-hi"
            >
              Walk the system <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <Card className="overflow-hidden">
            <pre className="overflow-x-auto p-5 text-xs leading-relaxed text-muted">
              {`upload  →  Docling parse  →  table → DuckDB facts
                          ↓
                       bge-m3 (dense + sparse)
                          ↓
                       Qdrant per-session
                          ↓
   query  →  expand  →  hybrid search  →  rerank
                          ↓
                       SSE: citations → tokens
                          ↓
                       tool calls → sandbox → audit`}
            </pre>
          </Card>
        </div>
      </section>

      {/* Tech stack */}
      <section className="border-t border-border/60 py-16">
        <div className="container-wide">
          <p className="text-sm text-muted">Built on</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {stack.map((t) => (
              <Badge key={t} variant="muted" className="text-sm">
                {t}
              </Badge>
            ))}
          </div>
        </div>
      </section>

      {/* Security */}
      <section className="border-t border-border/60 py-20">
        <div className="container-wide">
          <Card className="border-accent/30 bg-accent/5 p-8">
            <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <Badge variant="accent">Security model</Badge>
                <p className="mt-3 max-w-2xl text-pretty text-lg">
                  Your provider key lives in your tab's <code>sessionStorage</code>,
                  forwarded once per request in the <code>X-Provider-Key</code> header,
                  bound to the request and discarded. It is never written to disk,
                  never logged. Close the tab and it's gone.
                </p>
              </div>
              <Link href="/setup">
                <Button size="lg" variant="primary">
                  Set up a key <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </Card>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}
