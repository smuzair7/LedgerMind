"""Structural-first, semantic-fallback chunker.

Strategy:
  1. Walk the parsed document by section headings. Each section becomes one or
     more chunks.
  2. If a section exceeds a hard token budget, split with a sentence-aware
     splitter (`semantic_text_splitter.TextSplitter`, Rust-binding, no model
     load required for plain character/token-count splitting).
  3. Tables are NEVER merged with surrounding prose; each table is its own
     chunk type with the markdown body and a JSON preview retained in payload.

The chunk model is deliberately storage-agnostic — the embedder reads `text`
and the Qdrant upserter reads `payload`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from semantic_text_splitter import TextSplitter

ChunkKind = Literal["text", "table"]

DEFAULT_MAX_CHARS = 6000  # approximate cap; tuned for ~1.5K-token bge-m3 budget
DEFAULT_OVERLAP = 600


@dataclass(slots=True)
class Chunk:
    text: str                    # normalized, indexable
    raw_text: str                # original for display
    kind: ChunkKind
    page: int
    section_path: tuple[str, ...] = ()
    table_id: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    language: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


_splitter: TextSplitter | None = None


def _get_splitter(max_chars: int = DEFAULT_MAX_CHARS, overlap: int = DEFAULT_OVERLAP) -> TextSplitter:
    """Singleton splitter — purely deterministic, no model load."""
    global _splitter
    if _splitter is None:
        _splitter = TextSplitter(max_chars, overlap=overlap)
    return _splitter


def chunk_text(
    text: str,
    *,
    page: int,
    section_path: tuple[str, ...] = (),
    raw_text: str | None = None,
    language: str | None = None,
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap: int = DEFAULT_OVERLAP,
) -> list[Chunk]:
    """Split prose by sentence boundaries while staying under `max_chars`."""
    if not text.strip():
        return []
    splitter = _get_splitter(max_chars=max_chars, overlap=overlap)
    pieces = splitter.chunks(text)
    return [
        Chunk(
            text=piece,
            raw_text=piece if raw_text is None else raw_text,
            kind="text",
            page=page,
            section_path=section_path,
            language=language,
        )
        for piece in pieces
    ]


def make_table_chunk(
    *,
    markdown: str,
    raw_text: str,
    page: int,
    table_id: str,
    section_path: tuple[str, ...] = (),
    bbox: tuple[float, float, float, float] | None = None,
    language: str | None = None,
    json_preview: list[dict[str, object]] | None = None,
) -> Chunk:
    return Chunk(
        text=markdown,
        raw_text=raw_text,
        kind="table",
        page=page,
        section_path=section_path,
        table_id=table_id,
        bbox=bbox,
        language=language,
        payload={"table_preview": json_preview or []},
    )
