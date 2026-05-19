"""bge-reranker-v2-m3 via FastEmbed.

Lazy-loaded singleton — first call carries the ~1-2s model load. Reranks
candidate chunks by computing a cross-encoder score against the query.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from app.settings import get_infra

log = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


@dataclass(slots=True)
class RerankCandidate:
    payload: dict
    score_before: float


@dataclass(slots=True)
class RerankResult:
    payload: dict
    score_before: float
    score: float  # reranker score


def _get_reranker():  # type: ignore[no-untyped-def]
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from fastembed.rerank.cross_encoder import TextCrossEncoder

                name = get_infra().reranker_model
                log.info("loading reranker %s", name)
                _model = TextCrossEncoder(model_name=name)
    return _model


def rerank(
    query: str,
    candidates: list[RerankCandidate],
    *,
    top_k: int = 6,
) -> list[RerankResult]:
    if not candidates:
        return []
    try:
        model = _get_reranker()
        texts = [c.payload.get("text") or c.payload.get("raw_text") or "" for c in candidates]
        scores = list(model.rerank(query, texts))
        out = [
            RerankResult(payload=c.payload, score_before=c.score_before, score=float(s))
            for c, s in zip(candidates, scores, strict=True)
        ]
    except Exception as e:  # noqa: BLE001
        # If the reranker model can't load (e.g. offline portfolio review),
        # fall back to the upstream RRF scores so the system still works.
        log.warning("reranker fallback to upstream scores: %s", e)
        out = [
            RerankResult(payload=c.payload, score_before=c.score_before, score=c.score_before)
            for c in candidates
        ]
    out.sort(key=lambda r: r.score, reverse=True)
    return out[:top_k]
