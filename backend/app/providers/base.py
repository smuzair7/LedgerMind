"""Provider abstraction.

All LLM providers in Ledgermind speak the same `LLMProvider` Protocol. Each
implementation translates its vendor's streaming response and tool-call format
into a unified `StreamEvent` taxonomy. Providers are constructed per-request
with the user's BYO key — they are NOT singletons.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from app.schemas.chat import ChatMessage


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Provider-agnostic tool definition. Adapters translate to vendor format."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema


# --- Streaming event taxonomy ---


@dataclass(frozen=True, slots=True)
class TokenEvent:
    kind: Literal["token"] = "token"
    delta: str = ""


@dataclass(frozen=True, slots=True)
class ToolCallEvent:
    id: str
    name: str
    args: dict[str, Any]
    kind: Literal["tool_call"] = "tool_call"


@dataclass(frozen=True, slots=True)
class UsageEvent:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    kind: Literal["usage"] = "usage"


@dataclass(frozen=True, slots=True)
class DoneEvent:
    kind: Literal["done"] = "done"


@dataclass(frozen=True, slots=True)
class ErrorEvent:
    code: str
    message: str
    kind: Literal["error"] = "error"


StreamEvent = TokenEvent | ToolCallEvent | UsageEvent | DoneEvent | ErrorEvent


@runtime_checkable
class LLMProvider(Protocol):
    """Async streaming + tool-calling LLM interface."""

    name: str

    async def stream(
        self,
        *,
        messages: Sequence[ChatMessage],
        model: str,
        tools: Sequence[ToolSpec] | None = None,
        temperature: float = 0.2,
    ) -> AsyncIterator[StreamEvent]:
        ...

    async def validate(self, *, model: str | None = None) -> tuple[bool, str | None]:
        """Cheap key validation: 1-token completion (or model listing where supported)."""
        ...
