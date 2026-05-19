"""Generation orchestrator.

  retrieve → emit citations → assemble messages with cited context →
  provider.stream → forward events.

Tool-call loop (round-trip through the calculations sandbox) lands in
milestone #7. For now we forward provider events as-is.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import asdict

from app.generation.prompts import SYSTEM_PROMPT, language_hint
from app.providers.base import (
    DoneEvent,
    ErrorEvent,
    LLMProvider,
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    UsageEvent,
)
from app.retrieval.orchestrator import RetrievalResult, retrieve
from app.schemas.chat import ChatMessage, ChatRequest, Citation

log = logging.getLogger(__name__)

# Public event taxonomy for the SSE layer — the chat router translates these
# into wire frames via app.generation.stream.stream_event_to_sse plus a
# dedicated `citations` frame for the RetrievalResult.


async def run_chat(
    *,
    request: ChatRequest,
    provider: LLMProvider,
) -> AsyncIterator[tuple[str, dict]]:
    """Yield (event_name, payload_dict) tuples ready for SSE encoding.

    Why this shape: keeping the citations event distinct from StreamEvent lets
    the chat router emit it BEFORE any token arrives, with payloads that
    include the full Citation list (for the frontend's pre-render).
    """
    if not request.session_id:
        # No session → no retrieval; just stream the model's response.
        retrieval = RetrievalResult(citations=[], context_blocks=[], raw_payloads=[])
    else:
        try:
            retrieval = await retrieve(session_id=request.session_id, query=request.message)
        except Exception as e:  # noqa: BLE001
            log.warning("retrieval failed: %s", e)
            retrieval = RetrievalResult(citations=[], context_blocks=[], raw_payloads=[])

    yield (
        "citations",
        {"citations": [c.model_dump() for c in retrieval.citations]},
    )

    messages = _build_messages(request, retrieval.citations, retrieval.context_blocks)

    try:
        async for event in provider.stream(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
        ):
            yield _event_to_pair(event)
    except Exception as e:  # noqa: BLE001
        log.exception("generation failed")
        yield ("error", {"code": "internal", "message": str(e)})


def _build_messages(
    request: ChatRequest,
    citations: list[Citation],
    context_blocks: list[str],
) -> list[ChatMessage]:
    system = SYSTEM_PROMPT.strip() + "\n\n" + language_hint(request.language)
    if citations:
        system += (
            "\n\nYou are answering against indexed source documents. The user's "
            "question will be followed by a CONTEXT block containing numbered "
            "excerpts. When you make a claim that's grounded in a specific "
            "excerpt, cite it inline using the numeric label, e.g. [1]. Use "
            "those numbers and ONLY those numbers as citation markers."
        )
    context_text = ""
    if context_blocks:
        context_text = "\n\nCONTEXT:\n" + "\n\n---\n\n".join(context_blocks)
    user_content = request.message + context_text
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=user_content),
    ]


def _event_to_pair(event: StreamEvent) -> tuple[str, dict]:
    if isinstance(event, TokenEvent):
        return ("token", {"delta": event.delta})
    if isinstance(event, ToolCallEvent):
        return ("tool_call", {"id": event.id, "name": event.name, "args": event.args})
    if isinstance(event, UsageEvent):
        return (
            "usage",
            {
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "cache_read_tokens": event.cache_read_tokens,
                "cache_write_tokens": event.cache_write_tokens,
            },
        )
    if isinstance(event, DoneEvent):
        return ("done", {})
    if isinstance(event, ErrorEvent):
        return ("error", {"code": event.code, "message": event.message})
    return ("unknown", asdict(event))
