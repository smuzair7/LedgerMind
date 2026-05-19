from __future__ import annotations

from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    id: str = Field(description="Provider-specific model identifier.")
    label: str = Field(description="Human-friendly model name.")
    context_window: int | None = None
    supports_tools: bool = True
    family: str | None = None  # e.g. "gpt-4o", "claude-3.7", "gemini-2.0"


class ProviderInfo(BaseModel):
    id: str = Field(description="Stable provider identifier (e.g. 'openai', 'anthropic').")
    label: str
    description: str | None = None
    website: str | None = None
    key_url: str | None = None
    requires_key: bool = True
    models: list[ModelInfo]
    needs_base_url: bool = False  # true for `custom`


class ValidateRequest(BaseModel):
    provider: str
    model: str | None = None
    base_url: str | None = None  # used for custom OpenAI-compatible


class ValidateResponse(BaseModel):
    ok: bool
    detail: str | None = None
