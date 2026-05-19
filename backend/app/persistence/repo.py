from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.persistence.models import Document, Message, Session


def new_id() -> str:
    return uuid.uuid4().hex


async def create_session(db: AsyncSession, *, name: str | None = None) -> Session:
    sess = Session(id=new_id(), name=name or "New chat")
    db.add(sess)
    await db.flush()
    return sess


async def list_sessions(db: AsyncSession) -> list[tuple[Session, int]]:
    """Sessions plus doc count, newest first."""
    stmt = (
        select(Session, func.count(Document.id))
        .outerjoin(Document, Document.session_id == Session.id)
        .group_by(Session.id)
        .order_by(Session.created_at.desc())
    )
    result = await db.execute(stmt)
    return [(s, c or 0) for s, c in result.all()]


async def get_session(db: AsyncSession, session_id: str) -> Session | None:
    return await db.get(Session, session_id)


async def delete_session(db: AsyncSession, session_id: str) -> bool:
    sess = await db.get(Session, session_id)
    if sess is None:
        return False
    await db.delete(sess)
    return True


async def append_message(
    db: AsyncSession,
    *,
    session_id: str,
    role: str,
    content: str,
    citations_json: str | None = None,
    tool_calls_json: str | None = None,
    usage_json: str | None = None,
) -> Message:
    msg = Message(
        id=new_id(),
        session_id=session_id,
        role=role,
        content=content,
        citations_json=citations_json,
        tool_calls_json=tool_calls_json,
        usage_json=usage_json,
    )
    db.add(msg)
    await db.flush()
    return msg


async def list_messages(db: AsyncSession, session_id: str) -> list[Message]:
    stmt = select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
    result = await db.execute(stmt)
    return list(result.scalars())
