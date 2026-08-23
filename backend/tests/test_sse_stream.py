"""
Tests for the SSE progress stream. EventSource (the browser API the
frontend uses) can't set an Authorization header, so the stream route
authenticates via a `token` query param instead -- this locks that path in.

The full live event flow (agent_started/completed per node, tool calls,
budget updates, critic verdict, through to `completed`) is verified
against a REAL running uvicorn server rather than here: httpx's in-process
ASGITransport doesn't interleave a long-lived streaming response with a
separately-scheduled background asyncio task the way two real, separate
connections on a real server do, which makes "subscribe, then trigger
planning, then expect events in order" a source of test-harness race
conditions and hangs rather than a meaningful check of the actual
behavior. See docs/sample-sse-trace.md for that captured trace (27
events, every node, in order, ending in `completed`).
"""
from __future__ import annotations

import json

import pytest

CANONICAL_PROMPT = (
    "I want to visit Japan for 8 days in October. My budget is Rs 350000. "
    "I like nature, anime, food and photography. I dont like crowded tourist "
    "attractions. I am traveling with one friend. I prefer comfortable hotels "
    "and dont want extremely long travel days. I am flying from Mumbai."
)


class TestSSEStream:
    @pytest.mark.asyncio
    async def test_stream_rejects_missing_token(self, client, registered_user):
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=registered_user["headers"])
        trip_id = create.json()["id"]

        async with client.stream("GET", f"/api/trips/{trip_id}/stream") as resp:
            assert resp.status_code == 200  # SSE streams start 200, error is in-band
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    assert payload["type"] == "error"
                    break

    @pytest.mark.asyncio
    async def test_stream_rejects_invalid_token(self, client, registered_user):
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=registered_user["headers"])
        trip_id = create.json()["id"]

        async with client.stream("GET", f"/api/trips/{trip_id}/stream?token=not-a-real-token") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    assert payload["type"] == "error"
                    break

    @pytest.mark.asyncio
    async def test_stream_rejects_someone_elses_trip(self, client, registered_user):
        create = await client.post("/api/trips", json={"prompt": CANONICAL_PROMPT}, headers=registered_user["headers"])
        trip_id = create.json()["id"]

        other_email = "other-" + registered_user["email"]
        reg = await client.post("/api/auth/register", json={"email": other_email, "password": "testpass123"})
        other_token = reg.json()["access_token"]

        async with client.stream("GET", f"/api/trips/{trip_id}/stream?token={other_token}") as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    payload = json.loads(line[len("data:"):].strip())
                    assert payload["type"] == "error"
                    break
