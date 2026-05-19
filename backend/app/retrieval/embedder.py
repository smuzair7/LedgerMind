"""FastEmbed-backed dense + sparse embeddings.

`bge-m3` ships both modalities from a single model. We expose them as separate
functions because Qdrant accepts them as different named vectors.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from pathlib import Path

from app.settings import get_infra, get_settings

log = logging.getLogger(__name__)

_dense_model = None
_sparse_model = None
_lock = threading.Lock()


def _get_dense():  # type: ignore[no-untyped-def]
    global _dense_model
    if _dense_model is None:
        with _lock:
            if _dense_model is None:
                from fastembed import TextEmbedding

                model_name = get_infra().embedding_model
                log.info("loading dense embedder %s", model_name)
                _dense_model = TextEmbedding(model_name=model_name)
    return _dense_model


def _get_sparse():  # type: ignore[no-untyped-def]
    global _sparse_model
    if _sparse_model is None:
        with _lock:
            if _sparse_model is None:
                # SparseTextEmbedding is paired with bge-m3 in FastEmbed.
                from fastembed import SparseTextEmbedding

                log.info("loading sparse embedder BAAI/bge-m3 (sparse)")
                _sparse_model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")
    return _sparse_model


def embed_dense(texts: list[str]) -> list[list[float]]:
    model = _get_dense()
    return [list(v) for v in model.embed(texts, batch_size=32)]


def embed_dense_query(text: str) -> list[float]:
    model = _get_dense()
    return next(iter(model.query_embed([text])))  # type: ignore[no-any-return]


def embed_sparse(texts: list[str]) -> list[tuple[list[int], list[float]]]:
    model = _get_sparse()
    out: list[tuple[list[int], list[float]]] = []
    for v in model.embed(texts, batch_size=32):
        out.append((list(v.indices), list(v.values)))
    return out


def embed_sparse_query(text: str) -> tuple[list[int], list[float]]:
    model = _get_sparse()
    v = next(iter(model.query_embed([text])))
    return (list(v.indices), list(v.values))


# --- Optional sqlite-backed embedding cache --------------------------------

CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS embed_cache (
    key   TEXT PRIMARY KEY,
    dim   INTEGER NOT NULL,
    vec   BLOB    NOT NULL
);
"""


class EmbeddingCache:
    """SQLite cache keyed by sha256(model + normalized_text). Optional."""

    def __init__(self, path: Path | str | None = None) -> None:
        if path is None:
            path = Path(get_settings().data_dir) / "embed_cache.sqlite"
        self.path = str(path)
        self._con = sqlite3.connect(self.path, isolation_level=None)
        self._con.execute(CACHE_SCHEMA)

    def close(self) -> None:
        self._con.close()
