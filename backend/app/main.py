from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_setup import get_logger, setup_logging
from app.middleware.provider_key import ProviderKeyMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.persistence.db import init_db
from app.routers import chat, documents, health, jobs, providers, sessions
from app.settings import get_settings

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging(get_settings().log_level)
    await init_db()
    log.info("startup_complete")
    yield
    log.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Ledgermind",
        version="0.1.0",
        description="Bilingual financial-RAG backend with deterministic calculations.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(ProviderKeyMiddleware)
    app.add_middleware(RequestIDMiddleware)

    app.include_router(health.router)
    app.include_router(providers.router)
    app.include_router(sessions.router)
    app.include_router(documents.router)
    app.include_router(documents.documents_router)
    app.include_router(jobs.router)
    app.include_router(chat.router)

    return app


app = create_app()
