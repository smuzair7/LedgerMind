from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    document_id: str
    job_id: str
    name: str
    sha256: str
    inline: bool  # True if processed sync (no Redis)


class JobStatus(BaseModel):
    id: str
    document_id: str
    status: str
    progress: int
    error: str | None
    created_at: datetime
    updated_at: datetime


class DocumentInfo(BaseModel):
    id: str
    name: str
    sha256: str
    pages: int | None
    status: str
    created_at: datetime
