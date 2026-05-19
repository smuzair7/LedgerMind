from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
async def root() -> dict[str, str]:
    return {
        "name": "ledgermind",
        "docs": "/docs",
        "healthz": "/healthz",
    }
