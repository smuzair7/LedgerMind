# Backend

FastAPI app for Ledgermind. See [`../ARCHITECTURE.md`](../ARCHITECTURE.md) for the system context.

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Set `QDRANT_MODE=memory` for in-process Qdrant (no Docker, no persistence) when exploring.
