"""Retrieval orchestrator.

  expand → for each variant: dense + sparse → RRF (qdrant native) → fuse all
         variants via reciprocal-rank average → rerank → assemble citations.

The orchestrator returns both:
  - citations: list of Citation models for the SSE `citations` event.
  - context_blocks: typed strings to splice into the LLM prompt with [citation
    indices] inline so the model is encouraged to cite as it speaks.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.retrieval import qdrant_client
from app.retrieval.embedder import embed_dense_query, embed_sparse_query
from app.retrieval.reranker import RerankCandidate, rerank
from app.retrieval.rewrite import expand_query
from app.schemas.chat import Citation

log = logging.getLogger(__name__)


@dataclass(slots=True)
class RetrievalResult:
    citations: list[Citation]
    context_blocks: list[str]
    raw_payloads: list[dict[str, Any]]


async def retrieve(
    *,
    session_id: str,
    query: str,
    top_k: int = 6,
    pool_size: int = 20,
) -> RetrievalResult:
    variants = expand_query(query) or [query]

    async def _search_one(q: str) -> list[Any]:
        try:
            dense = embed_dense_query(q)
            sparse = embed_sparse_query(q)
        except Exception as e:  # noqa: BLE001
            log.warning("embed failed for variant: %s", e)
            return []
        try:
            return await qdrant_client.hybrid_search(
                session_id,
                dense_query=dense,
                sparse_query=sparse,
                limit=pool_size,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("qdrant hybrid_search failed: %s", e)
            return []

    # Fan out variant searches in parallel.
    results_per_variant = await asyncio.gather(*(_search_one(v) for v in variants))

    # Fuse: reciprocal-rank merge across variants.
    by_id: dict[str, dict[str, Any]] = {}
    rrf_scores: dict[str, float] = {}
    for variant_idx, results in enumerate(results_per_variant):
        for rank, point in enumerate(results):
            pid = str(point.id)
            payload = dict(point.payload or {})
            by_id.setdefault(pid, payload)
            # k=60 RRF constant — tested to work well across hybrid sources.
            rrf_scores[pid] = rrf_scores.get(pid, 0.0) + 1.0 / (60 + rank)

    if not by_id:
        return RetrievalResult(citations=[], context_blocks=[], raw_payloads=[])

    candidates = [
        RerankCandidate(payload=by_id[pid], score_before=score)
        for pid, score in sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)[:pool_size]
    ]

    reranked = rerank(query, candidates, top_k=top_k)

    citations: list[Citation] = []
    context_blocks: list[str] = []
    raw_payloads: list[dict[str, Any]] = []

    for i, r in enumerate(reranked, start=1):
        payload = r.payload
        text = payload.get("raw_text") or payload.get("text") or ""
        page = int(payload.get("page") or 0) or 1
        doc_id = str(payload.get("doc_id") or "")
        doc_name = str(payload.get("doc_name") or "")
        bbox = payload.get("bbox")
        cid = f"c{i}"
        citation = Citation(
            id=cid,
            doc_id=doc_id,
            doc_name=doc_name,
            page=page,
            bbox=tuple(bbox) if bbox else None,
            snippet=_short(text, 240),
        )
        citations.append(citation)
        context_blocks.append(f"[{i}] {doc_name} p.{page}\n{text.strip()}")
        raw_payloads.append(payload)

    return RetrievalResult(citations=citations, context_blocks=context_blocks, raw_payloads=raw_payloads)


def _short(text: str, n: int) -> str:
    s = " ".join(text.split())
    return s if len(s) <= n else s[: n - 1] + "…"
