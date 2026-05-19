"""SSE encoding for the chat stream.

Wraps provider StreamEvents into Server-Sent Events with explicit `event:` types
so the frontend can route them. Payloads are JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from app.providers.base import (
    DoneEvent,
    ErrorEvent,
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    UsageEvent,
)


def encode_event(event_name: str, data: dict[str, Any]) -> str:
    """Build a single SSE frame. Data is single-line JSON; multi-line is uncommon."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_name}\ndata: {payload}\n\n"


def stream_event_to_sse(event: StreamEvent) -> str:
    if isinstance(event, TokenEvent):
        return encode_event("token", {"delta": event.delta})
    if isinstance(event, ToolCallEvent):
        return encode_event("tool_call", {"id": event.id, "name": event.name, "args": event.args})
    if isinstance(event, UsageEvent):
        return encode_event(
            "usage",
            {
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "cache_read_tokens": event.cache_read_tokens,
                "cache_write_tokens": event.cache_write_tokens,
            },
        )
    if isinstance(event, DoneEvent):
        return encode_event("done", {})
    if isinstance(event, ErrorEvent):
        return encode_event("error", {"code": event.code, "message": event.message})
    # Fallback (shouldn't happen given the union is closed).
    return encode_event("unknown", asdict(event))
