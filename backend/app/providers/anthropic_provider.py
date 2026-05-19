"""Anthropic Claude provider.

Notes on Anthropic-specific quirks the adapter has to handle:
  - System prompt goes in `system=`, NOT in messages.
  - Tool-use streams as `content_block_start` (with tool_use) + a series of
    `content_block_delta` events whose `delta.type` is `input_json_delta`. We
    accumulate `partial_json` strings and parse once on `content_block_stop`.
  - `cache_control: ephemeral` is set per block to participate in prompt cache.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from anthropic import AsyncAnthropic
from anthropic._exceptions import APIStatusError, AuthenticationError

from app.providers.base import (
    DoneEvent,
    ErrorEvent,
    LLMProvider,
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    ToolSpec,
    UsageEvent,
)
from app.schemas.chat import ChatMessage


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key required")
        self._client = AsyncAnthropic(api_key=api_key)

    @staticmethod
    def _split_system(messages: Sequence[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        out: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
            elif m.role == "tool":
                out.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.tool_call_id or "",
                                "content": m.content,
                            }
                        ],
                    }
                )
            else:
                out.append({"role": m.role, "content": m.content})
        system = "\n\n".join(system_parts) if system_parts else None
        return system, out

    @staticmethod
    def _to_anthropic_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.parameters,
            }
            for t in tools
        ]

    async def stream(
        self,
        *,
        messages: Sequence[ChatMessage],
        model: str,
        tools: Sequence[ToolSpec] | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        system, anth_messages = self._split_system(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": anth_messages,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            kwargs["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        if tools:
            kwargs["tools"] = self._to_anthropic_tools(tools)

        try:
            stream_mgr = self._client.messages.stream(**kwargs)
            tool_blocks: dict[int, dict[str, Any]] = {}

            async with stream_mgr as stream:
                async for event in stream:
                    et = getattr(event, "type", None)
                    if et == "content_block_start":
                        block = getattr(event, "content_block", None)
                        if block is not None and getattr(block, "type", None) == "tool_use":
                            idx = event.index
                            tool_blocks[idx] = {
                                "id": block.id,
                                "name": block.name,
                                "args": "",
                            }
                    elif et == "content_block_delta":
                        delta = event.delta
                        dt = getattr(delta, "type", None)
                        if dt == "text_delta":
                            yield TokenEvent(delta=delta.text)
                        elif dt == "input_json_delta":
                            idx = event.index
                            if idx in tool_blocks:
                                tool_blocks[idx]["args"] += delta.partial_json
                    elif et == "content_block_stop":
                        idx = event.index
                        block = tool_blocks.pop(idx, None)
                        if block is not None:
                            try:
                                args = json.loads(block["args"] or "{}")
                            except json.JSONDecodeError:
                                args = {"_raw": block["args"]}
                            yield ToolCallEvent(id=block["id"], name=block["name"], args=args)
                    elif et == "message_delta":
                        usage = getattr(event, "usage", None)
                        if usage is not None:
                            yield UsageEvent(
                                completion_tokens=getattr(usage, "output_tokens", None),
                                cache_read_tokens=getattr(usage, "cache_read_input_tokens", None),
                                cache_write_tokens=getattr(usage, "cache_creation_input_tokens", None),
                            )
            yield DoneEvent()
        except AuthenticationError as e:
            yield ErrorEvent(code="auth", message=str(e))
        except APIStatusError as e:
            yield ErrorEvent(code="provider_error", message=str(e))

    async def validate(self, *, model: str | None = None) -> tuple[bool, str | None]:
        try:
            target = model or "claude-haiku-4-5"
            resp = await self._client.messages.create(
                model=target,
                max_tokens=1,
                messages=[{"role": "user", "content": "ping"}],
            )
            return (bool(resp.content), None)
        except AuthenticationError as e:
            return (False, f"auth: {e}")
        except APIStatusError as e:
            return (False, str(e))
