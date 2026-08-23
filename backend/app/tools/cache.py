"""Redis-backed cache for provider results. Every tool call goes through
`cached()` so identical searches within the TTL window don't re-hit
(mock or real) external APIs -- this is the caching layer required by
section 21 of the spec, tested for real against a local Redis instance."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable
from typing import TypeVar

import redis.asyncio as aioredis

from app.core.config import get_settings

T = TypeVar("T")

_redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
    return _redis_client


def make_cache_key(namespace: str, **kwargs) -> str:
    payload = json.dumps(kwargs, sort_keys=True, default=str)
    digest = hashlib.sha256(payload.encode()).hexdigest()[:24]
    return f"trip_planner:{namespace}:{digest}"


async def cached(
    key: str,
    ttl_seconds: int,
    fetch: Callable[[], Awaitable[list[dict] | dict]],
) -> tuple[list[dict] | dict, bool]:
    """Returns (value, was_cache_hit). `fetch` is only called on a miss."""
    r = get_redis()
    try:
        raw = await r.get(key)
    except Exception:
        raw = None  # Redis unavailable -- degrade to always-fetch rather than fail the request.
    if raw is not None:
        return json.loads(raw), True

    value = await fetch()
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        pass
    return value, False
