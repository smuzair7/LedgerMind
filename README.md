<div align="center">

# Ledgermind

**Read financial statements with a model that shows its work.**

Bilingual (English + Arabic) Retrieval-Augmented Generation for financial documents.
Cited every claim. Computed, not guessed. Streamed token-by-token. Multi-provider, BYO-key.

[Architecture](./ARCHITECTURE.md) · [Quickstart](#quickstart) · [Why this isn't a toy RAG](#why-this-isnt-a-toy-rag)

</div>

---

## What this is

Upload an annual report (English or Arabic). Ask anything. Get an answer where:

- Every claim links back to the exact page and bounding box in the source PDF.
- Every number is **computed by a deterministic tool call**, not hallucinated by the model. The tool result, formula, and source inputs are rendered alongside the answer.
- The response streams back token by token over Server-Sent Events.
- You bring your own API key from any major provider — OpenAI, Anthropic, Google Gemini, Mistral, Cohere, Groq, or any OpenAI-compatible endpoint.

## Why this isn't a toy RAG

| Concern | Most chat-with-PDF demos | Ledgermind |
|---|---|---|
| Parsing | `PyPDF2.extract_text()` — text only | Docling layout-aware extraction with table cell grids, page + bbox provenance, OCR fallback |
| Retrieval | Dense vectors, top-K | Hybrid dense + sparse with RRF fusion, then `bge-reranker-v2-m3` rerank |
| Bilingual | Translate query, translate answer | `bge-m3` indexes Arabic and English natively; Arabic normalization (NFKC, tatweel strip) at ingest |
| Calculations | "Pretty please compute gross margin" prompt | Structured table extraction → DuckDB facts → LLM tool-calls (`compute_ratio`, `compute_yoy`, …) → AST-sandboxed Python — every number is audited |
| Citations | None, or "see chunks above" | Citation chips in-stream; click to open the cited page with bbox highlight |
| Streaming | Wait for full response | First citations appear before the first token; tokens stream live |
| Providers | One vendor, hardcoded | Seven, swappable in the UI, validated per-key |
| Key handling | Hard-coded `.env` or sketchy text box | Browser sessionStorage → `X-Provider-Key` header → request-scoped, never persisted server-side, scrubbed from logs |

## Quickstart

> Requires Docker Desktop. Tested on Windows 11, macOS, Linux.

```bash
git clone https://github.com/smuzair7/LedgerMind.git
cd LedgerMind
cp .env.example .env
docker compose up --build
```

Then open `http://localhost:3000`. The first run downloads the `bge-m3` and reranker ONNX weights (~2 GB combined).

**Without Docker** (Qdrant in-memory, no persistence):

```bash
cd backend && uv sync && QDRANT_MODE=memory uv run uvicorn app.main:app --reload
# in another shell
cd web && pnpm install && pnpm dev
```

## Stack

**Backend:** FastAPI · Qdrant · DuckDB · arq · MinIO · FastEmbed (bge-m3 + bge-reranker-v2-m3) · Docling · official SDKs for OpenAI / Anthropic / Google / Mistral / Cohere / Groq.

**Frontend:** Next.js 15 (App Router) · TypeScript · Tailwind · shadcn/ui · Zustand · next-intl · react-pdf · Shiki.

## Project layout

```
LedgerMind/
├── backend/        FastAPI app, ingestion, retrieval, calculations
├── web/            Next.js 15 app
├── docs/           Diagrams + screenshots
├── docker-compose.yml
├── .env.example
└── ARCHITECTURE.md
```

## Security model

Your provider API key never touches our server's disk and never appears in logs. It is:

1. Stored in your browser's `sessionStorage` — cleared when you close the tab.
2. Forwarded once per request in the `X-Provider-Key` header.
3. Bound to `request.state` for the duration of that request, then discarded.
4. Scrubbed from request/response logs by middleware.

## Windows + OneDrive note

If you clone into a OneDrive-synced folder, exclude `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, and `volumes/` from sync (`Always keep on this device` off) — sync conflicts on those paths are a known source of slow builds.

## License

MIT. See [LICENSE](./LICENSE).
