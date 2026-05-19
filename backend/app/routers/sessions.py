from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.persistence import repo
from app.persistence.db import get_db
from app.schemas.sessions import SessionCreate, SessionInfo, SessionMessage

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionInfo)
async def create_session(payload: SessionCreate, db=Depends(get_db)) -> SessionInfo:  # type: ignore[no-untyped-def]
    sess = await repo.create_session(db, name=payload.name)
    await db.commit()
    return SessionInfo(id=sess.id, name=sess.name, created_at=sess.created_at, doc_count=0)


@router.get("", response_model=list[SessionInfo])
async def list_sessions(db=Depends(get_db)) -> list[SessionInfo]:  # type: ignore[no-untyped-def]
    rows = await repo.list_sessions(db)
    return [
        SessionInfo(id=s.id, name=s.name, created_at=s.created_at, doc_count=count)
        for s, count in rows
    ]


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str, db=Depends(get_db)) -> SessionInfo:  # type: ignore[no-untyped-def]
    sess = await repo.get_session(db, session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionInfo(id=sess.id, name=sess.name, created_at=sess.created_at, doc_count=0)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: str, db=Depends(get_db)) -> None:  # type: ignore[no-untyped-def]
    ok = await repo.delete_session(db, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found")
    await db.commit()


@router.get("/{session_id}/messages", response_model=list[SessionMessage])
async def list_messages(session_id: str, db=Depends(get_db)) -> list[SessionMessage]:  # type: ignore[no-untyped-def]
    msgs = await repo.list_messages(db, session_id)
    return [
        SessionMessage(id=m.id, role=m.role, content=m.content, created_at=m.created_at)
        for m in msgs
    ]
