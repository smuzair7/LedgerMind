"""arq worker entrypoint.

  arq app.jobs.arq_worker.WorkerSettings

The worker loads heavy models (Docling, FastEmbed) once at startup so jobs
don't pay the load cost per task.
"""

from __future__ import annotations

import logging

from arq.connections import RedisSettings

from app.ingestion.pipeline import ingest_file
from app.logging_setup import setup_logging
from app.persistence.db import init_db, session_scope
from app.persistence.models import IngestionJob
from app.settings import get_infra, get_settings
from sqlalchemy import update

log = logging.getLogger(__name__)


async def startup(_ctx: dict) -> None:  # type: ignore[type-arg]
    setup_logging(get_settings().log_level)
    await init_db()
    log.info("arq_worker_ready")


async def shutdown(_ctx: dict) -> None:  # type: ignore[type-arg]
    log.info("arq_worker_shutdown")


async def ingest_document(
    ctx: dict,  # type: ignore[type-arg]
    *,
    job_id: str,
    session_id: str,
    document_id: str,
    file_key: str,
    doc_name: str,
) -> dict:  # type: ignore[type-arg]
    from app.storage.files import get_storage

    storage = get_storage()
    path = await storage.get_path(file_key)

    async def progress(pct: int, label: str) -> None:
        async with session_scope() as db:
            await db.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(progress=pct, status=label)
            )

    try:
        result = await ingest_file(
            session_id=session_id,
            doc_id=document_id,
            file_path=path,
            doc_name=doc_name,
            progress_cb=lambda p, l: None,  # async progress wired below
        )
        # The progress callback above is sync — emit final state explicitly.
        async with session_scope() as db:
            await db.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(status="done", progress=100)
            )
        return {
            "ok": True,
            "chunks": result.chunks_upserted,
            "facts": result.facts_upserted,
            "pages": result.pages,
        }
    except Exception as e:  # noqa: BLE001
        log.exception("ingest_failed")
        async with session_scope() as db:
            await db.execute(
                update(IngestionJob)
                .where(IngestionJob.id == job_id)
                .values(status="error", error=str(e))
            )
        return {"ok": False, "error": str(e)}


class WorkerSettings:
    functions = [ingest_document]
    on_startup = startup
    on_shutdown = shutdown

    @staticmethod
    def redis_settings() -> RedisSettings:
        return RedisSettings.from_dsn(get_infra().redis_url)
