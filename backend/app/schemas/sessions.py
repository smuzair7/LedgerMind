from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    name: str | None = None


class SessionInfo(BaseModel):
    id: str
    name: str
    created_at: datetime
    doc_count: int = 0


class SessionMessage(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
