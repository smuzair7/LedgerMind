"""Per-request provider construction from (provider_id, api_key, base_url)."""

from __future__ import annotations

from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.gemini import GeminiProvider
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
    if pid == "google":
        return GeminiProvider(api_key)
    # Mistral and Cohere use OpenAI-compatible endpoints in practice; users
    # can reach them via the "custom" provider with their docs' base_url.
    # Dedicated adapters land alongside provider-normalize fixture tests.
    if pid in {"mistral", "cohere"}:
        raise UnknownProviderError(
            f"Provider '{pid}': use 'custom' for now with the provider's "
            "OpenAI-compatible base URL. Dedicated adapter coming."
        )
    raise UnknownProviderError(f"Unknown provider: {provider_id}")
