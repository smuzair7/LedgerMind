"""Extract the BYO provider key from the X-Provider-Key header.

The key is stashed on request.state.provider_key. It is NEVER logged. The
RequestIDMiddleware and structlog config strip Authorization / X-Provider-Key
from log output, but we also avoid putting the value anywhere that could leak.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

HEADER_NAME = "X-Provider-Key"


class ProviderKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        key = request.headers.get(HEADER_NAME)
        request.state.provider_key = key
        response: Response = await call_next(request)
        return response


def get_provider_key(request: Request) -> str | None:
    return getattr(request.state, "provider_key", None)
