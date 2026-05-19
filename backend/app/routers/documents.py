from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from app.ingestion.hashing import sha256_file
from app.jobs.queue import enqueue
from app.persistence import repo
from app.persistence.db import get_db, session_scope
from app.persistence.models import Document, IngestionJob
from app.schemas.ingest import DocumentInfo, UploadResponse
from app.settings import get_settings
from app.storage.files import get_storage

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions/{session_id}/documents", tags=["documents"])
documents_router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("", response_model=UploadResponse)
async def upload(
    session_id: str,
    file: UploadFile = File(...),
    db=Depends(get_db),  # type: ignore[no-untyped-def]
) -> UploadResponse:
    sess = await repo.get_session(db, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")

    name = file.filename or "document.pdf"
    if not name.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF uploads are supported")

    storage = get_storage()
    document_id = repo.new_id()
    file_key = f"{session_id}/{document_id}.pdf"
    await storage.put(file_key, file)

    # Compute sha256 from the staged file.
    staged_path = await storage.get_path(file_key)
    sha = sha256_file(staged_path)

    doc = Document(
        id=document_id,
        session_id=session_id,
        name=name,
        file_key=file_key,
        sha256=sha,
        status="queued",
    )
    db.add(doc)
    job = IngestionJob(id=repo.new_id(), document_id=document_id)
    db.add(job)
    await db.commit()

    # Try arq first; if no worker is available, run inline.
    arq_id = await enqueue(
        "ingest_document",
        job_id=job.id,
        session_id=session_id,
        document_id=document_id,
        file_key=file_key,
        doc_name=name,
    )

    if arq_id:
        return UploadResponse(
            document_id=document_id,
            job_id=job.id,
            name=name,
            sha256=sha,
            inline=False,
        )

    # No worker → in-process fallback. The API holds the request for the
    # duration of ingestion. Documented in the README as the no-Docker path.
    from app.jobs.arq_worker import ingest_document  # local import

    await ingest_document(
        {},
        job_id=job.id,
        session_id=session_id,
        document_id=document_id,
        file_key=file_key,
        doc_name=name,
    )
    return UploadResponse(
        document_id=document_id,
        job_id=job.id,
        name=name,
        sha256=sha,
        inline=True,
    )


@router.get("", response_model=list[DocumentInfo])
async def list_documents(session_id: str, db=Depends(get_db)) -> list[DocumentInfo]:  # type: ignore[no-untyped-def]
    stmt = (
        select(Document)
        .where(Document.session_id == session_id)
        .order_by(Document.created_at.desc())
    )
    res = await db.execute(stmt)
    docs = list(res.scalars())
    return [
        DocumentInfo(
            id=d.id,
            name=d.name,
            sha256=d.sha256,
            pages=d.pages,
            status=d.status,
            created_at=d.created_at,
        )
        for d in docs
    ]


@documents_router.get("/{document_id}/file")
async def get_file(document_id: str) -> FileResponse:
    async with session_scope() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")
        file_key = doc.file_key
        name = doc.name

    storage = get_storage()
    path: Path = await storage.get_path(file_key)
    return FileResponse(path, media_type="application/pdf", filename=name)
