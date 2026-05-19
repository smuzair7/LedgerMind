"""Smoke tests — confirm the app boots and core endpoints answer."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_healthz(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_list_providers(client):
    r = await client.get("/api/providers")
    assert r.status_code == 200
    body = r.json()
    ids = {p["id"] for p in body}
    assert {"openai", "anthropic", "google", "mistral", "cohere", "groq", "custom"} <= ids


async def test_chat_stream_requires_key(client):
    r = await client.post(
        "/api/chat/stream",
        json={
            "message": "hi",
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    )
    assert r.status_code == 400


async def test_create_and_list_session(client):
    r = await client.post("/api/sessions", json={"name": "first"})
    assert r.status_code == 200
    sid = r.json()["id"]

    r = await client.get("/api/sessions")
    assert r.status_code == 200
    assert any(s["id"] == sid for s in r.json())

    r = await client.delete(f"/api/sessions/{sid}")
    assert r.status_code == 204
