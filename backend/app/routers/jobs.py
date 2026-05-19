from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.persistence.db import get_db
from app.persistence.models import IngestionJob
from app.schemas.ingest import JobStatus

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: str, db=Depends(get_db)) -> JobStatus:  # type: ignore[no-untyped-def]
    job = await db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        id=job.id,
        document_id=job.document_id,
        status=job.status,
        progress=job.progress,
        error=job.error,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
