"""Structlog configuration with sensitive-header scrubbing."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

SCRUB_KEYS = frozenset(
    {
        "x-provider-key",
        "x_provider_key",
        "authorization",
        "api-key",
        "api_key",
        "openai-api-key",
        "anthropic-api-key",
    }
)


def _scrub_keys(_logger: object, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Replace any value at a sensitive key with `***scrubbed***`."""
    for key in list(event_dict.keys()):
        if key.lower() in SCRUB_KEYS:
            event_dict[key] = "***scrubbed***"
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _scrub_dict(event_dict[key])
    return event_dict


def _scrub_dict(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if k.lower() in SCRUB_KEYS:
            out[k] = "***scrubbed***"
        elif isinstance(v, dict):
            out[k] = _scrub_dict(v)
        else:
            out[k] = v
    return out


def setup_logging(level: str = "info") -> None:
    """Configure structlog + stdlib logging once at app start."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _scrub_keys,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
