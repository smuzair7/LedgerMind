# Ledgermind

A bilingual (English / Arabic) retrieval-augmented generation system for financial documents. Answers cite the source page, numeric values are produced by deterministic tool calls rather than free generation, and responses stream over Server-Sent Events. Provider keys are user-supplied and live only in the browser tab.

## Table of contents

- [Features](#features)
- [Architecture](#architecture)
- [Stack](#stack)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Security model](#security-model)
- [Development](#development)
- [Project layout](#project-layout)
- [License](#license)

## Features

- **Bilingual retrieval.** Arabic and English are indexed in the same vector space via `bge-m3`. Arabic text is normalized at ingest (NFKC, tatweel removal, alef / ya folding) and Arabic-Indic digits are translated for numeric parsing.
- **Hybrid search.** Per-session Qdrant collections with both dense and sparse vectors, fused with reciprocal-rank fusion and reranked with `bge-reranker-v2-m3`.
- **Layout-aware ingestion.** Docling extracts paragraphs and tables with page and bounding-box provenance. An OCR fallback covers scanned pages.
- **Deterministic calculations.** Tables are parsed into typed facts (`statement`, `period`, `line_item`, `value`, `currency`, `unit_scale`) and stored in per-session DuckDB. The model invokes named tools — `lookup_line_item`, `compute_yoy`, `compute_ratio` (twelve named ratios), `cagr`, and a sandboxed `python_eval` — and returns the formula, inputs (each linked to its source fact), and the computed value.
- **Streaming.** Tagged SSE events: `citations`, `token`, `tool_call`, `tool_result`, `usage`, `done`, `error`. Citations are emitted before the first token.
- **Multiple providers.** Direct adapters for OpenAI, Anthropic, Google Gemini, and Groq, plus a generic OpenAI-compatible adapter for endpoints such as Mistral, Cohere, OpenRouter, Together, vLLM, and llama.cpp.
- **Bring-your-own-key.** API keys are kept in browser `sessionStorage`, forwarded per request in the `X-Provider-Key` header, bound to `request.state` for the duration of the request, and scrubbed from logs.

## Architecture

```
upload → Docling parse → tables → DuckDB facts
                       ↓
                    bge-m3 (dense + sparse)
                       ↓
                    Qdrant per-session collection

query  → expand → hybrid search → rerank → citations
                                              ↓
                       generation orchestrator (tool-call loop)
                                              ↓
                       SSE: citations → tokens → tool_calls → tool_results → done
```

A longer walk-through with rationale for each choice lives in [ARCHITECTURE.md](./ARCHITECTURE.md) and is mirrored in-app at `/architecture`.

## Stack

| Layer | Components |
|---|---|
| Backend | FastAPI, Pydantic v2, SQLAlchemy 2 (async), Docling, FastEmbed (`bge-m3`, `bge-reranker-v2-m3`), Qdrant, DuckDB, arq, MinIO |
| LLM SDKs | `openai`, `anthropic`, `google-genai`, `groq` |
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Zustand, `react-markdown` |
| Infrastructure | Docker Compose, Redis |

## Quickstart

Requires Docker Desktop. Tested on Windows 11, macOS, and Linux.

```bash
git clone https://github.com/smuzair7/LedgerMind.git
cd LedgerMind
cp .env.example .env
docker compose up --build
```

Open `http://localhost:3000`. From the landing page, follow the setup flow to pick a provider, choose a model, and paste an API key. The backend validates the key with a one-token completion before the chat UI is unlocked. Drag a PDF onto the document panel to ingest it; once parsing, embedding, and indexing complete, ask a question.

The first run downloads model weights (`bge-m3` ~1.1 GB, reranker ~0.6 GB) into a Docker volume.

### Running without Docker

A no-Docker dev mode is available, with Qdrant in-process (no persistence):

```bash
cd backend
pip install -e .
QDRANT_MODE=memory uvicorn app.main:app --reload

# in a second shell
cd web
pnpm install
pnpm dev
```

## Configuration

All configuration lives in `.env`. Provider API keys are never set here — they are user-supplied at runtime. See `.env.example` for the full list. Notable variables:

| Variable | Default | Purpose |
|---|---|---|
| `LEDGERMIND_DATABASE_URL` | `sqlite+aiosqlite:///./data/ledgermind.db` | Session/message metadata. Swap for Postgres via `postgresql+asyncpg://…`. |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant endpoint. Set `QDRANT_MODE=memory` to use an in-process instance. |
| `REDIS_URL` | `redis://redis:6379/0` | arq job queue. The API falls back to in-process ingestion if unreachable. |
| `S3_ENDPOINT` | unset | MinIO / S3 endpoint. When unset, files are stored on the local disk under `./data/files/`. |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | Override the default embedding model. |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | Override the default cross-encoder. |
| `LEDGERMIND_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowlist. |

## Security model

Provider API keys are not persisted server-side. The path is:

1. The browser stores the key in `sessionStorage`; it is cleared when the tab is closed.
2. Each API call attaches the key in the `X-Provider-Key` header.
3. `ProviderKeyMiddleware` reads the header into `request.state.provider_key`, where it is available to the request-scoped provider adapter.
4. The structlog configuration includes a processor that replaces values at sensitive keys (`X-Provider-Key`, `Authorization`, `api-key`, vendor-specific variants) with `***scrubbed***` before any log line is rendered.

The relevant files are short and worth reading directly: [`backend/app/middleware/provider_key.py`](backend/app/middleware/provider_key.py) and [`backend/app/logging_setup.py`](backend/app/logging_setup.py).

## Development

### Backend

```bash
cd backend
pip install -e '.[dev]'

ruff check .
mypy app
pytest -q
```

Tests cover Arabic normalization, table extraction, content hashing, the per-session facts store, the AST-whitelisted Python sandbox, and a few smoke endpoints.

### Frontend

```bash
cd web
pnpm install
pnpm typecheck
pnpm lint
pnpm build
```

### OneDrive on Windows

If the repository is cloned into a OneDrive-synced folder, exclude `node_modules/`, `.next/`, `.venv/`, `__pycache__/`, and `volumes/` from sync. Sync conflicts on those paths slow builds noticeably.

## Project layout

```
LedgerMind/
├── backend/
│   ├── app/
│   │   ├── providers/        LLM adapters (openai_compat, anthropic, gemini)
│   │   ├── ingestion/        Docling parse, table extraction, chunking, Arabic normalization
│   │   ├── retrieval/        Hybrid orchestrator, reranker, query rewriting
│   │   ├── calculations/     Tool catalog, AST-whitelisted sandbox, audit
│   │   ├── generation/       SSE encoder, retrieve → stream → tool-call loop
│   │   ├── jobs/             arq worker and queue
│   │   ├── routers/          chat, sessions, documents, jobs, providers
│   │   ├── persistence/      SQLAlchemy 2.0 async models and repo
│   │   └── storage/          MinIO and local-disk file storage
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
├── web/
│   ├── app/                  landing, setup, chat, architecture, SSE proxy
│   ├── components/           ui primitives, chat surface, document panel
│   ├── lib/                  api-client, sse, providers, auth-store, chat-api
│   ├── hooks/                use-chat-stream
│   ├── package.json
│   └── Dockerfile
├── docs/
│   ├── diagrams/
│   └── screenshots/
├── docker-compose.yml
├── .env.example
├── ARCHITECTURE.md
└── README.md
```

## License

[MIT](./LICENSE).
