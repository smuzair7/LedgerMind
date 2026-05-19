"""Generation orchestrator with tool-call loop.

  retrieve → emit citations → assemble messages → provider.stream
                                                        ↓
                                          tool_call ← loop → tool result
                                                        ↓
                                               final tokens → done

The loop terminates when the provider stops emitting tool calls (or after a
small bound to prevent runaway loops). Each tool result is sent back to the
provider as a `tool` role message so the next turn can use it.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from dataclasses import asdict

from app.calculations.audit import ToolAudit
from app.calculations.tools import ToolError, all_tools, run_tool
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

MAX_TOOL_ROUNDS = 4


async def run_chat(
    *,
    request: ChatRequest,
    provider: LLMProvider,
) -> AsyncIterator[tuple[str, dict]]:
    if not request.session_id:
        retrieval = RetrievalResult(citations=[], context_blocks=[], raw_payloads=[])
    else:
        try:
            retrieval = await retrieve(session_id=request.session_id, query=request.message)
        except Exception as e:  # noqa: BLE001
            log.warning("retrieval failed: %s", e)
            retrieval = RetrievalResult(citations=[], context_blocks=[], raw_payloads=[])

    yield ("citations", {"citations": [c.model_dump() for c in retrieval.citations]})

    messages = _build_messages(request, retrieval.citations, retrieval.context_blocks)
    tools = all_tools() if request.tools_enabled else None

    for round_idx in range(MAX_TOOL_ROUNDS):
        pending_tool_calls: list[tuple[str, str, dict]] = []  # (id, name, args)
        try:
            async for event in provider.stream(
                messages=messages,
                model=request.model,
                tools=tools,
                temperature=request.temperature,
            ):
                pair = _event_to_pair(event)
                if isinstance(event, ToolCallEvent):
                    pending_tool_calls.append((event.id, event.name, event.args))
                # Surface every event except `done` — we may need another turn.
                if isinstance(event, DoneEvent):
                    continue
                yield pair
        except Exception as e:  # noqa: BLE001
            log.exception("generation failed mid-round")
            yield ("error", {"code": "internal", "message": str(e)})
            return

        if not pending_tool_calls:
            yield ("done", {})
            return

        # Append assistant turn marker (we don't see the full assistant content
        # for non-OpenAI providers cleanly, so we send a placeholder note)
        # and then the tool result messages.
        assistant_note = "(invoked tools: " + ", ".join(t[1] for t in pending_tool_calls) + ")"
        messages.append(ChatMessage(role="assistant", content=assistant_note))

        for tool_id, tool_name, tool_args in pending_tool_calls:
            result, audit = _run_one_tool(request.session_id, tool_name, tool_args)
            yield (
                "tool_result",
                {
                    "id": tool_id,
                    "ok": audit.ok,
                    "result": result,
                    "audit": audit.to_dict(),
                },
            )
            messages.append(
                ChatMessage(
                    role="tool",
                    name=tool_name,
                    tool_call_id=tool_id,
                    content=_tool_result_to_text(result, audit),
                )
            )

    # Hit the round bound.
    yield ("error", {"code": "tool_loop_bound", "message": f"Stopped after {MAX_TOOL_ROUNDS} tool rounds"})


def _run_one_tool(session_id: str | None, name: str, args: dict) -> tuple[dict, ToolAudit]:
    if not session_id:
        audit = ToolAudit(tool=name, args=args, ok=False, result=None, error="no session_id")
        return ({"error": "no session_id"}, audit)
    try:
        result = run_tool(session_id=session_id, name=name, args=args)
        audit = ToolAudit(tool=name, args=args, ok=True, result=result)
        return (result, audit)
    except ToolError as e:
        audit = ToolAudit(tool=name, args=args, ok=False, result=None, error=f"{e.code}: {e.message}")
        return ({"error": e.message, "code": e.code}, audit)
    except Exception as e:  # noqa: BLE001
        log.exception("tool execution crashed")
        audit = ToolAudit(tool=name, args=args, ok=False, result=None, error=str(e))
        return ({"error": str(e)}, audit)


def _tool_result_to_text(result: dict, audit: ToolAudit) -> str:
    if not audit.ok:
        return f"TOOL_ERROR: {audit.error}"
    formula = result.get("formula", "")
    value = result.get("value")
    return f"value={value} formula='{formula}'"


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
            "excerpts. Cite excerpts inline as [1], [2], …, using ONLY those "
            "numeric labels."
        )
    system += (
        "\n\nWhen the user asks for any number that requires a lookup or "
        "calculation, you MUST call a tool. Tools are deterministic and their "
        "results are auditable; values you produce on your own are not "
        "trusted by the user. Available tools: lookup_line_item, compute_yoy, "
        "compute_ratio (named ratios), cagr, python_eval."
    )
    context_text = "\n\nCONTEXT:\n" + "\n\n---\n\n".join(context_blocks) if context_blocks else ""
    return [
        ChatMessage(role="system", content=system),
        ChatMessage(role="user", content=request.message + context_text),
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
