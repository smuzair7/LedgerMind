"""POST /api/chat/stream — SSE chat endpoint.

For the MVP this thin endpoint:
  - validates the X-Provider-Key
  - builds the per-request provider
  - assembles the message list (system prompt + canned context for now)
  - streams provider events through the SSE encoder

Retrieval, tool-calling, and citation events are wired in later milestones
(#6 Hybrid retrieval, #7 Calculations). The SSE event taxonomy is stable from
day one so the frontend can be built against it.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.generation.prompts import SYSTEM_PROMPT, language_hint
from app.generation.stream import stream_event_to_sse
from app.middleware.provider_key import get_provider_key
from app.providers.registry import UnknownProviderError, build_provider
from app.schemas.chat import ChatMessage, ChatRequest

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

    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=SYSTEM_PROMPT + "\n\n" + language_hint(payload.language)),
        ChatMessage(role="user", content=payload.message),
    ]

    async def event_iter() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in provider.stream(
                messages=messages,
                model=payload.model,
                temperature=payload.temperature,
            ):
                frame = stream_event_to_sse(event)
                lines = frame.split("\n", 2)
                event_name = lines[0].removeprefix("event: ")
                data_line = lines[1].removeprefix("data: ")
                yield {"event": event_name, "data": data_line}
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
