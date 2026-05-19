"""Google Gemini provider (google-genai SDK).

Quirks the adapter normalizes:
  - System prompt goes in `system_instruction`, NOT in `contents`.
  - Roles in `contents` are "user" and "model" (not "assistant").
  - Tool schemas are JSON Schema with capital-cased types — google-genai
    accepts plain dicts here but with a slightly different shape; we let
    the SDK coerce by passing JSON Schema fragments.
  - Streaming emits Candidates whose parts may be text or function_call.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator, Sequence
from typing import Any

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

log = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "google"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("api_key required")
        # Lazy import so non-Google users don't pay the SDK load.
        from google import genai

        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _split_system(messages: Sequence[ChatMessage]) -> tuple[str | None, list[dict[str, Any]]]:
        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []
        for m in messages:
            if m.role == "system":
                system_parts.append(m.content)
                continue
            role = "model" if m.role == "assistant" else "user" if m.role == "user" else "user"
            if m.role == "tool":
                # Function results go back as a user turn with a function_response part.
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "function_response": {
                                    "name": m.name or "tool",
                                    "response": {"value": m.content},
                                }
                            }
                        ],
                    }
                )
                continue
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return ("\n\n".join(system_parts) if system_parts else None, contents)

    @staticmethod
    def _to_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "function_declarations": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    }
                    for t in tools
                ]
            }
        ]

    async def stream(
        self,
        *,
        messages: Sequence[ChatMessage],
        model: str,
        tools: Sequence[ToolSpec] | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        system, contents = self._split_system(messages)
        config: dict[str, Any] = {"temperature": temperature}
        if system:
            config["system_instruction"] = system
        if tools:
            config["tools"] = self._to_tools(tools)

        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=model, contents=contents, config=config
            )
            async for chunk in stream:
                # text parts
                for cand in chunk.candidates or []:
                    parts = (cand.content.parts if cand.content else []) or []
                    for part in parts:
                        if getattr(part, "text", None):
                            yield TokenEvent(delta=part.text)
                        fc = getattr(part, "function_call", None)
                        if fc is not None:
                            args = dict(fc.args) if fc.args else {}
                            # Gemini doesn't issue an id; synthesize one.
                            tc_id = f"gemini-{fc.name}-{abs(hash(json.dumps(args, sort_keys=True))) % 10_000_000}"
                            yield ToolCallEvent(id=tc_id, name=fc.name, args=args)
                usage = getattr(chunk, "usage_metadata", None)
                if usage is not None:
                    yield UsageEvent(
                        prompt_tokens=getattr(usage, "prompt_token_count", None),
                        completion_tokens=getattr(usage, "candidates_token_count", None),
                        cache_read_tokens=getattr(usage, "cached_content_token_count", None),
                    )
            yield DoneEvent()
        except Exception as e:  # noqa: BLE001
            log.exception("gemini stream failed")
            yield ErrorEvent(code="provider_error", message=str(e))

    async def validate(self, *, model: str | None = None) -> tuple[bool, str | None]:
        try:
            target = model or "gemini-2.0-flash-lite"
            resp = await self._client.aio.models.generate_content(
                model=target,
                contents=[{"role": "user", "parts": [{"text": "ping"}]}],
                config={"max_output_tokens": 1, "temperature": 0},
            )
            return (bool(resp.candidates), None)
        except Exception as e:  # noqa: BLE001
            return (False, str(e))
