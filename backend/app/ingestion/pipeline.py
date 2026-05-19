"""End-to-end ingestion orchestrator.

  parse → normalize → chunk → tables → embed → upsert
                          ↘ facts → DuckDB

Designed to run inside the arq worker. Idempotent: re-ingesting the same PDF
(by sha256) is a no-op because Qdrant upserts use a deterministic chunk hash
as the point id and DuckDB facts use a deterministic fact id.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.calculations.facts_store import FactsStore, store_path
from app.ingestion.arabic import looks_arabic, normalize_arabic
from app.ingestion.chunking import Chunk, chunk_text, make_table_chunk
from app.ingestion.hashing import chunk_hash, sha256_file
from app.ingestion.parser_docling import ParsedDocument, parse_pdf
from app.ingestion.tables import extract_facts
from app.retrieval import qdrant_client
from app.retrieval.embedder import embed_dense, embed_sparse
from app.settings import get_settings

log = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestionResult:
    doc_id: str
    sha256: str
    pages: int
    chunks_upserted: int
    facts_upserted: int


async def ingest_file(
    *,
    session_id: str,
    doc_id: str,
    file_path: Path | str,
    doc_name: str,
    progress_cb: callable | None = None,  # type: ignore[valid-type]
) -> IngestionResult:
    """Parse, chunk, embed, upsert. Returns counts for telemetry."""
    file_path = Path(file_path)
    sha = sha256_file(file_path)

    _step(progress_cb, 5, "parsing")
    parsed: ParsedDocument = parse_pdf(file_path)
    _step(progress_cb, 35, "chunking")
    chunks = _build_chunks(parsed)
    _step(progress_cb, 45, "extracting facts")
    facts_count = _persist_facts(session_id=session_id, doc_id=doc_id, parsed=parsed)
    _step(progress_cb, 55, "embedding")
    upserted = await _embed_and_upsert(
        session_id=session_id,
        doc_id=doc_id,
        doc_name=doc_name,
        chunks=chunks,
        progress_cb=progress_cb,
    )
    _step(progress_cb, 100, "done")

    return IngestionResult(
        doc_id=doc_id,
        sha256=sha,
        pages=parsed.page_count,
        chunks_upserted=upserted,
        facts_upserted=facts_count,
    )


def _step(cb: callable | None, pct: int, label: str) -> None:  # type: ignore[valid-type]
    if cb is None:
        return
    try:
        cb(pct, label)
    except Exception:  # noqa: BLE001
        pass


def _build_chunks(parsed: ParsedDocument) -> list[Chunk]:
    out: list[Chunk] = []
    for section in parsed.sections:
        is_ar = looks_arabic(section.text)
        normalized = normalize_arabic(section.text) if is_ar else section.text
        out.extend(
            chunk_text(
                normalized,
                page=section.page,
                section_path=section.section_path,
                raw_text=section.text,
                language="ar" if is_ar else "en",
            )
        )
    for table in parsed.tables:
        markdown = table.markdown or _grid_to_markdown(table.cells)
        is_ar = looks_arabic(markdown)
        out.append(
            make_table_chunk(
                markdown=normalize_arabic(markdown) if is_ar else markdown,
                raw_text=markdown,
                page=table.page,
                table_id=table.table_id,
                section_path=table.section_path,
                bbox=table.bbox,
                language="ar" if is_ar else "en",
                json_preview=[
                    {f"col{i}": cell for i, cell in enumerate(row)} for row in table.cells[:5]
                ],
            )
        )
    return out


def _grid_to_markdown(cells: list[list[str]]) -> str:
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    norm = [r + [""] * (width - len(r)) for r in cells]
    header = "| " + " | ".join(norm[0]) + " |"
    sep = "| " + " | ".join(["---"] * width) + " |"
    body = "\n".join("| " + " | ".join(r) + " |" for r in norm[1:])
    return "\n".join([header, sep, body])


def _persist_facts(*, session_id: str, doc_id: str, parsed: ParsedDocument) -> int:
    if not parsed.tables:
        return 0
    settings = get_settings()
    path = store_path(settings.data_dir, session_id)
    total = 0
    with FactsStore(path) as store:
        for table in parsed.tables:
            facts = extract_facts(session_id=session_id, doc_id=doc_id, table=table)
            if facts:
                total += store.upsert_many(facts)
    return total


async def _embed_and_upsert(
    *,
    session_id: str,
    doc_id: str,
    doc_name: str,
    chunks: list[Chunk],
    progress_cb: callable | None,  # type: ignore[valid-type]
) -> int:
    if not chunks:
        return 0
    texts = [c.text for c in chunks]
    dense = embed_dense(texts)
    _step(progress_cb, 80, "sparse encoding")
    sparse = embed_sparse(texts)

    ids: list[str] = []
    payloads: list[dict[str, Any]] = []
    for c in chunks:
        cid = chunk_hash(doc_id=doc_id, page=c.page, text=c.text, table_id=c.table_id)
        ids.append(cid)
        payload: dict[str, Any] = {
            "doc_id": doc_id,
            "doc_name": doc_name,
            "page": c.page,
            "section_path": list(c.section_path),
            "chunk_type": c.kind,
            "language": c.language,
            "raw_text": c.raw_text,
            "text": c.text,
        }
        if c.bbox is not None:
            payload["bbox"] = list(c.bbox)
        if c.table_id:
            payload["table_id"] = c.table_id
        payload.update(c.payload)
        payloads.append(payload)

    _step(progress_cb, 90, "indexing")
    await qdrant_client.upsert_chunks(
        session_id,
        ids=ids,
        dense=dense,
        sparse=sparse,
        payloads=payloads,
    )
    return len(ids)
