"""Static metadata catalog of providers and their commonly-used models.

Kept hand-curated rather than dynamically fetched because (a) the providers
disagree on what /v1/models returns (Groq exposes everything; Anthropic has no
public list endpoint without a key; Gemini changes endpoints regularly) and
(b) hand-curation lets us label context windows and tool-support correctly.

Override / extend by editing this file. The frontend reads from
GET /api/providers which serializes this catalog.
"""

from __future__ import annotations

from app.schemas.providers import ModelInfo, ProviderInfo

PROVIDERS: list[ProviderInfo] = [
    ProviderInfo(
        id="openai",
        label="OpenAI",
        description="GPT-4o, o-series reasoning, GPT-4.1.",
        website="https://openai.com",
        key_url="https://platform.openai.com/api-keys",
        models=[
            ModelInfo(id="gpt-4o", label="GPT-4o", context_window=128_000, family="gpt-4o"),
            ModelInfo(id="gpt-4o-mini", label="GPT-4o mini", context_window=128_000, family="gpt-4o"),
            ModelInfo(id="gpt-4.1", label="GPT-4.1", context_window=1_000_000, family="gpt-4.1"),
            ModelInfo(id="gpt-4.1-mini", label="GPT-4.1 mini", context_window=1_000_000, family="gpt-4.1"),
            ModelInfo(id="o3-mini", label="o3-mini", context_window=200_000, family="o", supports_tools=True),
        ],
    ),
    ProviderInfo(
        id="anthropic",
        label="Anthropic",
        description="Claude — strong on long-context reasoning and tool use.",
        website="https://anthropic.com",
        key_url="https://console.anthropic.com/settings/keys",
        models=[
            ModelInfo(id="claude-opus-4-7", label="Claude Opus 4.7", context_window=1_000_000, family="claude-4"),
            ModelInfo(id="claude-sonnet-4-6", label="Claude Sonnet 4.6", context_window=200_000, family="claude-4"),
            ModelInfo(id="claude-haiku-4-5", label="Claude Haiku 4.5", context_window=200_000, family="claude-4"),
        ],
    ),
    ProviderInfo(
        id="google",
        label="Google",
        description="Gemini 2.x — strong multimodal and long context.",
        website="https://ai.google.dev",
        key_url="https://aistudio.google.com/app/apikey",
        models=[
            ModelInfo(id="gemini-2.0-flash", label="Gemini 2.0 Flash", context_window=1_000_000),
            ModelInfo(id="gemini-2.0-flash-lite", label="Gemini 2.0 Flash Lite", context_window=1_000_000),
            ModelInfo(id="gemini-1.5-pro", label="Gemini 1.5 Pro", context_window=2_000_000),
            ModelInfo(id="gemini-1.5-flash", label="Gemini 1.5 Flash", context_window=1_000_000),
        ],
    ),
    ProviderInfo(
        id="mistral",
        label="Mistral",
        description="Mistral Large / Small with tool use.",
        website="https://mistral.ai",
        key_url="https://console.mistral.ai/api-keys/",
        models=[
            ModelInfo(id="mistral-large-latest", label="Mistral Large", context_window=131_072),
            ModelInfo(id="mistral-small-latest", label="Mistral Small", context_window=131_072),
            ModelInfo(id="open-mistral-nemo", label="Mistral Nemo", context_window=131_072),
        ],
    ),
    ProviderInfo(
        id="cohere",
        label="Cohere",
        description="Command R — strong RAG and citations.",
        website="https://cohere.com",
        key_url="https://dashboard.cohere.com/api-keys",
        models=[
            ModelInfo(id="command-r-plus-08-2024", label="Command R+ (08-2024)", context_window=128_000),
            ModelInfo(id="command-r-08-2024", label="Command R (08-2024)", context_window=128_000),
        ],
    ),
    ProviderInfo(
        id="groq",
        label="Groq",
        description="Very fast inference of Llama, Mixtral, Qwen.",
        website="https://groq.com",
        key_url="https://console.groq.com/keys",
        models=[
            ModelInfo(id="llama-3.3-70b-versatile", label="Llama 3.3 70B Versatile", context_window=131_072),
            ModelInfo(id="llama-3.1-8b-instant", label="Llama 3.1 8B Instant", context_window=131_072),
            ModelInfo(id="qwen-2.5-32b", label="Qwen 2.5 32B", context_window=131_072),
        ],
    ),
    ProviderInfo(
        id="custom",
        label="Custom (OpenAI-compatible)",
        description="OpenRouter, Together, vLLM, llama.cpp — any OpenAI-compatible endpoint.",
        website=None,
        key_url=None,
        needs_base_url=True,
        models=[
            ModelInfo(id="auto", label="(specify in chat)", context_window=None),
        ],
    ),
]


def by_id(provider_id: str) -> ProviderInfo | None:
    return next((p for p in PROVIDERS if p.id == provider_id), None)
