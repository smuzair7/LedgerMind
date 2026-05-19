"""OpenAI + any OpenAI-compatible provider (Groq, Together, OpenRouter, vLLM, llama.cpp).

This single adapter handles all OpenAI Chat Completions-flavored APIs by varying
the `base_url`. The streaming response and tool-call shape are identical across
these endpoints.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from typing import Any

from openai import AsyncOpenAI
from openai._exceptions import AuthenticationError, OpenAIError, RateLimitError

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

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class OpenAICompatProvider(LLMProvider):
    name: str

    def __init__(self, api_key: str, *, base_url: str | None = None, name: str = "openai") -> None:
        if not api_key:
            raise ValueError("api_key required")
        self.name = name
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @classmethod
    def for_openai(cls, api_key: str) -> OpenAICompatProvider:
        return cls(api_key, name="openai")

    @classmethod
    def for_groq(cls, api_key: str) -> OpenAICompatProvider:
        return cls(api_key, base_url=GROQ_BASE_URL, name="groq")

    @classmethod
    def for_custom(cls, api_key: str, base_url: str) -> OpenAICompatProvider:
        if not base_url:
            raise ValueError("base_url required for custom provider")
        return cls(api_key, base_url=base_url, name="custom")

    @staticmethod
    def _to_openai_messages(messages: Sequence[ChatMessage]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            entry: dict[str, Any] = {"role": m.role, "content": m.content}
            if m.role == "tool":
                if m.tool_call_id is None:
                    raise ValueError("tool message requires tool_call_id")
                entry["tool_call_id"] = m.tool_call_id
            if m.name:
                entry["name"] = m.name
            out.append(entry)
        return out

    @staticmethod
    def _to_openai_tools(tools: Sequence[ToolSpec]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
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
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": self._to_openai_messages(messages),
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            kwargs["tools"] = self._to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        # Accumulate streamed tool-call argument deltas keyed by index.
        tool_state: dict[int, dict[str, Any]] = {}

        try:
            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    if chunk.usage:
                        yield UsageEvent(
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                        )
                    continue

                delta = chunk.choices[0].delta
                if delta.content:
                    yield TokenEvent(delta=delta.content)

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        state = tool_state.setdefault(idx, {"id": "", "name": "", "args": ""})
                        if tc.id:
                            state["id"] = tc.id
                        if tc.function is not None:
                            if tc.function.name:
                                state["name"] += tc.function.name
                            if tc.function.arguments:
                                state["args"] += tc.function.arguments

                finish = chunk.choices[0].finish_reason
                if finish == "tool_calls":
                    for state in tool_state.values():
                        import json as _json

                        try:
                            args = _json.loads(state["args"] or "{}")
                        except _json.JSONDecodeError:
                            args = {"_raw": state["args"]}
                        yield ToolCallEvent(id=state["id"], name=state["name"], args=args)
                    tool_state.clear()

            yield DoneEvent()
        except AuthenticationError as e:
            yield ErrorEvent(code="auth", message=str(e))
        except RateLimitError as e:
            yield ErrorEvent(code="rate_limit", message=str(e))
        except OpenAIError as e:
            yield ErrorEvent(code="provider_error", message=str(e))

    async def validate(self, *, model: str | None = None) -> tuple[bool, str | None]:
        try:
            target = model or "gpt-4o-mini"
            # Smallest possible completion. Some custom endpoints reject max_tokens=0; use 1.
            resp = await self._client.chat.completions.create(
                model=target,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                temperature=0,
            )
            return (bool(resp.choices), None)
        except AuthenticationError as e:
            return (False, f"auth: {e}")
        except OpenAIError as e:
            return (False, str(e))
