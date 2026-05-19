from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    role: Role
    content: str
    tool_call_id: str | None = None
    name: str | None = None


class Citation(BaseModel):
    id: str
    doc_id: str
    doc_name: str
    page: int
    bbox: tuple[float, float, float, float] | None = None
    snippet: str | None = None


class ToolCall(BaseModel):
    id: str
    name: str
    args: dict[str, Any]


class ToolResult(BaseModel):
    id: str
    ok: bool
    result: Any
    audit: dict[str, Any] | None = None
    error: str | None = None


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    provider: str
    model: str
    base_url: str | None = None  # for `custom` provider
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    tools_enabled: bool = True
    language: Literal["en", "ar", "both"] = "en"


# --- SSE event payloads (tagged via `event` field on the SSE frame) ---


class CitationsEvent(BaseModel):
    citations: list[Citation]


class TokenEvent(BaseModel):
    delta: str


class ToolCallEvent(BaseModel):
    call: ToolCall


class ToolResultEvent(BaseModel):
    result: ToolResult


class UsageEvent(BaseModel):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None


class DoneEvent(BaseModel):
    message_id: str


class ErrorEvent(BaseModel):
    code: str
    message: str
