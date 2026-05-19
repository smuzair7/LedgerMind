from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def chunk_hash(*, doc_id: str, page: int, text: str, table_id: str | None = None) -> str:
    """Deterministic hash for a chunk so re-ingestion is idempotent."""
    h = hashlib.sha256()
    h.update(doc_id.encode())
    h.update(b"\x1f")
    h.update(str(page).encode())
    if table_id:
        h.update(b"\x1f")
        h.update(table_id.encode())
    h.update(b"\x1f")
    h.update(text.encode())
    return h.hexdigest()
