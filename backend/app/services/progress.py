"""
Every agent node calls `emit()` at key points (start, completion, tool
call, critic verdict, replanning). Each call does two things:
  1. Persists an AgentEvent row (durable history, section 6/22 of the spec)
  2. Publishes the same payload on a Redis pub/sub channel so any open
     SSE connection for this trip sees it immediately (section 19)

A fresh short-lived DB session is used per call (rather than sharing the
request's session) because nodes in the parallel research branches run
concurrently, and a single AsyncSession is not safe for concurrent use.
"""
from __future__ import annotations

import json
import time
from typing import Callable

import app.db.session as db_session_module
from app.models.agent import AgentEvent
from app.tools.cache import get_redis


def _channel(trip_id: str) -> str:
    return f"trip_planner:events:{trip_id}"


async def emit_event(
    session_factory: Callable,
    trip_id: str,
    agent_run_id: str,
    event_type: str,
    agent_name: str | None = None,
    message: str | None = None,
    payload: dict | None = None,
) -> None:
    payload = payload or {}
    record = {
        "type": event_type,
        "agent": agent_name,
        "message": message,
        "payload": payload,
        "ts": time.time(),
    }

    try:
        async with session_factory() as session:
            session.add(AgentEvent(
                agent_run_id=agent_run_id, event_type=event_type,
                agent_name=agent_name, message=message, payload=payload,
            ))
            await session.commit()
    except Exception:
        pass  # Progress logging must never break the planning run itself.

    try:
        r = get_redis()
        await r.publish(_channel(trip_id), json.dumps(record, default=str))
    except Exception:
        pass


async def subscribe(trip_id: str):
    """Async generator yielding decoded event dicts as they're published."""
    r = get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_channel(trip_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(_channel(trip_id))
        await pubsub.close()
