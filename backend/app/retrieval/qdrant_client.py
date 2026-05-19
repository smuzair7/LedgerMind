"""Per-session Qdrant collection management with hybrid (dense + sparse) vectors.

Collections are named `sess_{session_id}` and bootstrapped lazily on first
upsert. Drop on session delete is a single API call.
"""

from __future__ import annotations

import logging
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchAny,
    PointStruct,
    Prefetch,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.settings import get_infra

log = logging.getLogger(__name__)

DENSE_NAME = "dense"
SPARSE_NAME = "sparse"
DENSE_DIM = 1024  # bge-m3

_client: AsyncQdrantClient | None = None


def get_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        infra = get_infra()
        if infra.qdrant_mode == "memory":
            _client = AsyncQdrantClient(location=":memory:")
        else:
            _client = AsyncQdrantClient(url=infra.qdrant_url, api_key=infra.qdrant_api_key)
    return _client


def collection_for(session_id: str) -> str:
    return f"sess_{session_id}"


async def ensure_collection(session_id: str) -> None:
    client = get_client()
    name = collection_for(session_id)
    existing = await client.collection_exists(name)
    if existing:
        return
    await client.create_collection(
        collection_name=name,
        vectors_config={DENSE_NAME: VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={SPARSE_NAME: SparseVectorParams(index=SparseIndexParams(on_disk=False))},
    )
    # Useful payload indexes for filtering.
    for field in ("doc_id", "language", "chunk_type"):
        try:
            await client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema="keyword",
            )
        except Exception as e:  # noqa: BLE001
            log.debug("payload index already present or failed: %s", e)


async def drop_collection(session_id: str) -> None:
    client = get_client()
    try:
        await client.delete_collection(collection_for(session_id))
    except Exception as e:  # noqa: BLE001
        log.debug("delete_collection no-op: %s", e)


async def upsert_chunks(
    session_id: str,
    *,
    ids: list[str],
    dense: list[list[float]],
    sparse: list[tuple[list[int], list[float]]],
    payloads: list[dict[str, Any]],
) -> None:
    assert len(ids) == len(dense) == len(sparse) == len(payloads), "len mismatch"
    client = get_client()
    name = collection_for(session_id)
    await ensure_collection(session_id)
    points = [
        PointStruct(
            id=pid,
            vector={
                DENSE_NAME: dvec,
                SPARSE_NAME: SparseVector(indices=svec[0], values=svec[1]),
            },
            payload=payload,
        )
        for pid, dvec, svec, payload in zip(ids, dense, sparse, payloads, strict=True)
    ]
    await client.upsert(collection_name=name, points=points)


async def hybrid_search(
    session_id: str,
    *,
    dense_query: list[float],
    sparse_query: tuple[list[int], list[float]],
    limit: int = 20,
    doc_ids: list[str] | None = None,
) -> list[Any]:
    client = get_client()
    name = collection_for(session_id)
    flt = None
    if doc_ids:
        flt = Filter(must=[FieldCondition(key="doc_id", match=MatchAny(any=doc_ids))])
    result = await client.query_points(
        collection_name=name,
        prefetch=[
            Prefetch(
                query=dense_query,
                using=DENSE_NAME,
                limit=50,
                filter=flt,
            ),
            Prefetch(
                query=SparseVector(indices=sparse_query[0], values=sparse_query[1]),
                using=SPARSE_NAME,
                limit=50,
                filter=flt,
            ),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )
    return list(result.points)
