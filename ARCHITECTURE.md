# Ledgermind — Architecture

> Mirror of the `/architecture` page in the web app. This file walks the system from upload to streamed answer, and explains the design choices behind each layer.

## System overview

```
┌────────┐    upload     ┌─────────────────────────┐
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
│        │   │  emit `citations` event                          │
│        │   │  loop:                                           │
│        │   │   - provider.stream(messages, tools)             │
│        │   │   - on tool_call: run sandboxed calc → audit     │
│        │   │   - emit `token`, `tool_call`, `tool_result`     │
│        │   │  emit `done` + `usage`                           │
│        │   └──────────────────────────────────────────────────┘
│        │           │
│        ▼           ▼
│   ┌────────────────────┐
│   │ SSE proxy (Edge)   │
│   │ web/app/api/proxy  │
│   └────────────────────┘
└──── stream renders: chips first, then tokens, then calc cards
```

## Why these choices

(Each section will be expanded as the corresponding feature lands. See `docs/diagrams/` for source diagrams.)

### Parsing — Docling
Layout-aware table extraction with row/col cell grids and per-cell bbox. Open-source, no API dependency. Used vs. PyMuPDF+pdfplumber (heavy glue for nested tables), Unstructured hi-res (slower with worse table fidelity), LlamaParse (hosted only).

### Embeddings — `bge-m3` via FastEmbed
Multilingual (100+ languages including Arabic), 1024-dim dense + native sparse vectors from one model, ONNX runtime, runs on CPU. The dual dense+sparse output makes hybrid retrieval a single inference call.

### Retrieval — hybrid + rerank
Qdrant native RRF fusion over dense and sparse prefetches, then `bge-reranker-v2-m3` reranks top-20 → top-6. Skipped HyDE: for financial QA it tends to hallucinate plausible-looking numbers that pollute retrieval.

### Calculations — structured facts + sandboxed Python
Post-ingest pass writes typed facts (`{statement, period, line_item, value, currency, bbox}`) to DuckDB. LLM emits `compute_ratio`, `compute_yoy`, etc.; an AST-whitelisted Python evaluator runs the formula. Every numeric answer cites both source pages and the formula.

### Providers — official SDKs only
LangChain's streaming + tool-calling abstraction adds latency and breaks on minor SDK upgrades. Direct SDKs (`openai`, `anthropic`, `google-genai`, `mistralai`, `cohere`, `groq`) + a ~300-line normalization layer is the smaller, faster surface.

### Sessions — per-session Qdrant collection + DuckDB file
Drop-collection on session delete is trivial; no cross-session payload-filter overhead; payload-filter recall is noticeably worse on Qdrant when the filter is highly selective.

### Job queue — arq
Async-native, Redis-backed, ~one-file worker. Celery is heavyweight; RQ is sync-first; FastAPI BackgroundTasks dies with the process.

## Event taxonomy (SSE)

| Event | Payload | When |
|---|---|---|
| `citations` | `{citations: [{doc_id, page, bbox, snippet}]}` | Before first token |
| `token` | `{delta: "..."}` | Per provider chunk |
| `tool_call` | `{id, name, args}` | LLM requests a tool |
| `tool_result` | `{id, ok, result, audit}` | Sandbox returns |
| `usage` | `{prompt, completion, cache_hit_tokens?}` | Provider usage |
| `done` | `{message_id}` | Stream complete |
| `error` | `{code, message}` | Any failure |

The frontend renders citation chips as soon as `citations` arrives — long before the first `token` — so users see grounding visibly precede the answer.
