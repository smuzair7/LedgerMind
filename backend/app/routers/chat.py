"""POST /api/chat/stream — SSE chat endpoint.

The router does the cheap part: provider construction + key checks. The full
retrieve → generate pipeline lives in app.generation.orchestrator.run_chat.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.generation.orchestrator import run_chat
from app.middleware.provider_key import get_provider_key
from app.providers.registry import UnknownProviderError, build_provider
from app.schemas.chat import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> EventSourceResponse:
    key = get_provider_key(request)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Provider-Key header",
        )
    try:
        provider = build_provider(payload.provider, api_key=key, base_url=payload.base_url)
    except UnknownProviderError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    async def event_iter() -> AsyncIterator[dict[str, str]]:
        try:
            async for event_name, payload_dict in run_chat(request=payload, provider=provider):
                yield {
                    "event": event_name,
                    "data": json.dumps(payload_dict, ensure_ascii=False),
                }
        except Exception as e:  # noqa: BLE001
            yield {
                "event": "error",
                "data": json.dumps({"code": "internal", "message": str(e)}),
            }

    return EventSourceResponse(
        event_iter(),
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )
