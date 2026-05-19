<div align="center">

# Ledgermind

**Read financial statements with a model that shows its work.**

Bilingual (English + Arabic) Retrieval-Augmented Generation for financial documents.
Cited every claim. Computed, not guessed. Streamed token-by-token.
Multi-provider, BYO-key.

[Architecture](./ARCHITECTURE.md) · [Quickstart](#quickstart) · [Why this isn't a toy RAG](#why-this-isnt-a-toy-rag) · [Security model](#security-model)

</div>

---

## What this is

Upload an annual report (English or Arabic). Ask anything. Get an answer where:

- **Every claim cites its source.** Citation chips appear in the stream *before* the first generated token, so grounding visibly precedes the answer. Click a chip and the document viewer jumps to that page with the bounding box highlighted.
- **Every number is computed by a tool call, not guessed.** Ledgermind extracts structured facts at ingest time, and the model invokes deterministic tools (`compute_ratio`, `compute_yoy`, `cagr`, …) that run in an AST-whitelisted Python sandbox. Each result includes the formula, the inputs (each linked to its source fact), and the value — rendered as an auditable card alongside the prose answer.
- **Tokens stream live.** Server-Sent Events with a tagged taxonomy (`citations` · `token` · `tool_call` · `tool_result` · `usage` · `done` · `error`). The UI renders citation chips and calculation cards inline as they arrive.
- **You bring your own key.** OpenAI, Anthropic, Google Gemini, Groq, or any OpenAI-compatible endpoint (covers Mistral, Cohere, OpenRouter, Together, vLLM, llama.cpp). Keys live in `sessionStorage`, are forwarded once per request, and are never persisted on disk or logged.

## Why this isn't a toy RAG

| Concern | Most chat-with-PDF demos | Ledgermind |
|---|---|---|
| **PDF parsing** | `PyPDF2.extract_text()` — text only | Docling layout-aware extraction with table cell grids, page + bbox provenance, OCR fallback for scanned docs |
| **Retrieval** | Dense vectors, top-K | Hybrid dense + sparse (`bge-m3` ships both from one model) → RRF fusion via Qdrant native → `bge-reranker-v2-m3` rerank top-20 → top-6 |
| **Query** | Pass straight to the index | Lightweight expansion: Arabic-normalized variant when AR detected; period-focused variant when FY/Q/H tokens are present |
| **Bilingual** | Translate query, translate answer | `bge-m3` indexes Arabic and English natively in the same vector space. Arabic normalization (NFKC, tatweel strip, alef/ya folding) at ingest |
| **Calculations** | "Pretty please compute gross margin" prompt | Structured table extraction → DuckDB facts → LLM tool-calls executed in a sandbox → every number cites its inputs + formula |
| **Citations** | None, or "see chunks above" | Citation chips in-stream; click to open the cited page with bbox highlight |
| **Streaming** | Wait for full response | First citations appear before the first token; tokens stream live; stop mid-stream supported |
| **Providers** | One vendor, hardcoded | Five direct adapters (OpenAI, Anthropic, Google, Groq, custom OpenAI-compatible) + a tested normalization layer for tool-call quirks across vendors |
| **Key handling** | Hard-coded `.env` or sketchy text box | Browser `sessionStorage` → `X-Provider-Key` header → bound to `request.state` for the request, then discarded. Scrubbed from logs by middleware |
| **Streaming markdown** | Re-parse markdown every token (jank) | Plain-text render during stream, single text-node mutation per token; swap to full `react-markdown` on `done` |
| **State of the art** | Stops at LangChain abstractions | Direct vendor SDKs + ~300-line normalization layer. Smaller surface, less latency, breaks visibly when SDKs drift (contract tests pinned to fixtures) |

## Quickstart

> Requires Docker Desktop. Tested on Windows 11, macOS, Linux.

```bash
git clone https://github.com/smuzair7/LedgerMind.git
cd LedgerMind
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:3000` and:

1. **Landing → "Try with your key"**
2. **Setup** — pick a provider, pick a model, paste your API key, click **Validate**. The backend pings the provider with a one-token completion; specific errors (401 / 403 / 429) surface inline.
3. **Chat** — drag a financial-statement PDF onto the right panel. Watch the ingestion bar move through *Parsing → Embedding → Indexing*. Once it lands, ask:
   - *"What was revenue in FY2024?"* → citation chips appear, then the streamed answer.
   - *"Compute gross margin for FY2024."* → a CalculationCard renders with the formula, inputs (each a clickable citation), and the result.

The first run downloads `bge-m3` (~1.1 GB) and the reranker (~0.6 GB) ONNX weights into a Docker volume.

### Without Docker (Qdrant in-memory, no persistence)

```bash
cd backend && pip install -e . && QDRANT_MODE=memory uvicorn app.main:app --reload
# in another shell
cd web && pnpm install && pnpm dev
```

This skips Docker entirely — useful for browsing the code or running the API surface. Documents disappear when the API restarts.

## Stack

**Backend** · FastAPI · Qdrant (hybrid dense + sparse) · DuckDB (per-session facts) · arq (Redis job queue) · MinIO (S3-compatible files) · FastEmbed (`bge-m3` + `bge-reranker-v2-m3`) · Docling · Pydantic v2 · official SDKs for OpenAI / Anthropic / Google / Groq

**Frontend** · Next.js 15 (App Router) · React 19 · TypeScript · Tailwind · shadcn-style hand-rolled UI · Zustand (sessionStorage-hydrated) · react-markdown

**Infrastructure** · Docker Compose · MIT

## Project layout

```
LedgerMind/
├── backend/
│   ├── app/
│   │   ├── providers/        adapters (openai_compat, anthropic, gemini)
│   │   ├── ingestion/        Docling parse → tables → chunks → arabic norm
│   │   ├── retrieval/        hybrid orchestrator + reranker + query rewrite
│   │   ├── calculations/     tools (12 named ratios + CAGR + YoY) + sandbox
│   │   ├── generation/       SSE encoder + retrieve→stream→tool-loop orchestrator
│   │   ├── jobs/             arq worker + queue
│   │   ├── routers/          chat / sessions / documents / jobs / providers
│   │   ├── persistence/      SQLAlchemy 2.0 async models + repo
│   │   └── storage/          MinIO + local-disk fallback
│   ├── tests/                arabic norm, table extraction, sandbox, facts, smoke
│   ├── pyproject.toml
│   └── Dockerfile
├── web/
│   ├── app/                  landing · setup · chat · architecture · SSE proxy
│   ├── components/           ui/* + chat/* (CalculationCard, CitationChip, …)
│   ├── lib/                  api-client, sse, providers, auth-store, chat-api
│   ├── hooks/                use-chat-stream (reducer-driven token loop)
│   ├── tailwind.config.ts
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── diagrams/             mermaid + SVG sources
│   └── screenshots/          screenshots (landing, chat, calc card, …)
├── docker-compose.yml        qdrant + redis + minio + backend + worker + web
├── .env.example              infra only — NO provider keys live server-side
├── ARCHITECTURE.md
└── README.md
```

## Security model

Your provider API key never touches our server's disk and never appears in logs. The path is:

1. **Browser** — you paste your key on `/setup`. It's stored in this tab's `sessionStorage`. Closing the tab discards it.
2. **Request** — every API call adds an `X-Provider-Key` header. The backend's `ProviderKeyMiddleware` reads it into `request.state.provider_key` and continues.
3. **Use** — the per-request provider adapter is constructed from that value. It's never written to disk, never echoed in responses, never persisted in the database.
4. **Logs** — `structlog` runs a `_scrub_keys` processor over every record that replaces values at sensitive keys (`X-Provider-Key`, `Authorization`, `api-key`, vendor-specific variants) with `***scrubbed***`.

If you don't trust the host you're running this on, you shouldn't trust this — read [`backend/app/middleware/provider_key.py`](backend/app/middleware/provider_key.py) and [`backend/app/logging_setup.py`](backend/app/logging_setup.py); they're short.

## Architecture

A walk through what happens between "upload PDF" and a streamed answer with citations and audited numbers lives in [ARCHITECTURE.md](./ARCHITECTURE.md) and is mirrored in-app at `/architecture`.

```
upload  →  Docling parse  →  table → DuckDB facts
                       ↓
                    bge-m3 (dense + sparse)
                       ↓
                    Qdrant per-session collection
                       ↓
query  →  expand  →  hybrid search  →  rerank
                       ↓
                    SSE: citations → tokens → tool_calls → tool_results → done
                       ↓
                    UI: chips, streaming markdown, audited calc cards
```

## Windows + OneDrive note

If you clone into a OneDrive-synced folder, exclude `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, and `volumes/` from sync (`Always keep on this device` off) — sync conflicts on those paths are a known source of slow builds.

## License

MIT. See [LICENSE](./LICENSE).
