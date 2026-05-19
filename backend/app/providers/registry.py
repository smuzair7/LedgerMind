"""Per-request provider construction from (provider_id, api_key, base_url)."""

from __future__ import annotations

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.openai_compat import OpenAICompatProvider


class UnknownProviderError(ValueError):
    pass


def build_provider(
    provider_id: str,
    *,
    api_key: str,
    base_url: str | None = None,
) -> LLMProvider:
    pid = provider_id.lower().strip()
    if pid == "openai":
        return OpenAICompatProvider.for_openai(api_key)
    if pid == "groq":
        return OpenAICompatProvider.for_groq(api_key)
    if pid == "custom":
        if not base_url:
            raise ValueError("custom provider requires base_url")
        return OpenAICompatProvider.for_custom(api_key, base_url)
    if pid == "anthropic":
        return AnthropicProvider(api_key)
    # The following providers are scaffolded but their adapters are added in a
    # later milestone (#8 — Remaining providers). For now they raise so the
    # frontend doesn't silently submit chats to a missing adapter.
    if pid in {"google", "mistral", "cohere"}:
        raise UnknownProviderError(
            f"Provider '{pid}' is in the catalog but its adapter is not wired yet."
        )
    raise UnknownProviderError(f"Unknown provider: {provider_id}")
