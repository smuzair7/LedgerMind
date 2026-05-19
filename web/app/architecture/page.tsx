import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";

export const metadata = {
  title: "Ledgermind — Architecture",
};

export default function ArchitecturePage() {
  return (
    <div className="min-h-screen">
      <SiteHeader />
      <main className="container-tight py-16">
        <Link
          href="/"
          className="mb-6 inline-flex items-center gap-1 text-sm text-muted hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" /> Back
        </Link>

        <Badge variant="accent">Architecture</Badge>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight">The system, end to end</h1>
        <p className="mt-3 max-w-2xl text-muted">
          A walk through what happens between &ldquo;upload PDF&rdquo; and a streamed answer with
          citations and audited numbers. The interactive node-by-node view lands
          in milestone #10; this page sketches the shape.
        </p>

        <Card className="mt-10 overflow-hidden">
          <pre className="overflow-x-auto p-6 text-xs leading-relaxed text-muted">
{`┌────────┐    upload     ┌─────────────────────────┐
│  Web   │ ─────────────▶│  FastAPI /documents     │──┐
│ (Next) │               └─────────────────────────┘  │ enqueue
│        │                                            ▼
│        │                              ┌───────────────────────┐
│        │                              │  arq worker (Redis)   │
│        │                              │  Docling parse        │
│        │                              │  table extraction     │
│        │                              │  bilingual chunking   │
│        │                              │  bge-m3 embeddings    │
│        │                              │  Qdrant + DuckDB      │
│        │                              └───────────────────────┘
│        │
│        │    POST /api/chat/stream (SSE, X-Provider-Key)
│        │ ───────────────────────────────────────────────────┐
│        │                                                    ▼
│        │   ┌──────────────────────────────────────────────────┐
│        │   │ Retrieval orchestrator                           │
│        │   │  - query expansion                               │
│        │   │  - Qdrant hybrid (dense+sparse, RRF)             │
│        │   │  - bge-reranker-v2-m3                            │
│        │   │  - assemble citations                            │
│        │   └──────────────────────────────────────────────────┘
│        │           │
│        │           ▼
│        │   ┌──────────────────────────────────────────────────┐
│        │   │ Generation orchestrator                          │
│        │   │  emit 'citations' event                          │
│        │   │  loop:                                           │
│        │   │   - provider.stream(messages, tools)             │
│        │   │   - on tool_call: run sandboxed calc → audit     │
│        │   │   - emit token | tool_call | tool_result         │
│        │   │  emit 'done' + 'usage'                           │
│        │   └──────────────────────────────────────────────────┘
│        │           │
│        ▼           ▼
│   ┌────────────────────┐
│   │ SSE proxy (Edge)   │
│   │ web/app/api/proxy  │
│   └────────────────────┘
└──── stream renders: chips first, then tokens, then calc cards`}
          </pre>
        </Card>

        <section className="mt-12 grid gap-5 sm:grid-cols-2">
          <Highlight title="No LangChain">
            Direct vendor SDKs + ~300-line normalization layer. Smaller surface,
            less latency, breaks visibly when SDKs drift.
          </Highlight>
          <Highlight title="Per-session collection">
            Each chat has its own Qdrant collection. Delete = drop collection.
            Cleaner ACL, better hybrid recall than payload-filtered global stores.
          </Highlight>
          <Highlight title="Calculations as tools">
            <code>compute_ratio</code>, <code>compute_yoy</code>, <code>cagr</code>, …
            executed in an AST-whitelisted Python sandbox. Every number cites its
            inputs and its formula.
          </Highlight>
          <Highlight title="Streaming-first SSE">
            Citations event fires <em>before</em> the first token. Tool results
            arrive as discrete events. The UI renders chips and calculation cards
            inline.
          </Highlight>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}

function Highlight({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <Card className="p-5">
      <div className="text-sm font-semibold text-ink">{title}</div>
      <p className="mt-1 text-sm text-muted">{children}</p>
    </Card>
  );
}
