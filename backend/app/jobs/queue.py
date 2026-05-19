"""arq queue accessor. Lazy connection so the API process boots without Redis.

If REDIS_URL is unreachable, callers fall back to running the job in-process
(synchronously) — useful for the no-Docker dev path documented in the README.
"""

from __future__ import annotations

import logging
from typing import Any

from arq.connections import ArqRedis, RedisSettings, create_pool

from app.settings import get_infra

log = logging.getLogger(__name__)

_pool: ArqRedis | None = None


async def get_pool() -> ArqRedis | None:
    global _pool
    if _pool is not None:
        return _pool
    try:
        infra = get_infra()
        _pool = await create_pool(RedisSettings.from_dsn(infra.redis_url))
        return _pool
    except Exception as e:  # noqa: BLE001
        log.warning("arq pool unavailable, jobs will run in-process: %s", e)
        return None


async def enqueue(func_name: str, *args: Any, **kwargs: Any) -> str | None:
    pool = await get_pool()
    if pool is None:
        return None
    job = await pool.enqueue_job(func_name, *args, **kwargs)
    return job.job_id if job else None
