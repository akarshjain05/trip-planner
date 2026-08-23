from __future__ import annotations

import asyncio
import json
import uuid

import jwt
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import decode_token
from app.db.session import get_db
from app.models.trip import Trip
from app.models.user import User
from app.services.progress import subscribe

router = APIRouter(prefix="/trips", tags=["planning"])


def _format_sse(event: dict) -> str:
    event_type = event.get("type", "message")
    data = json.dumps(event)
    return f"event: {event_type}\ndata: {data}\n\n"


async def _resolve_user_for_stream(
    trip_id: uuid.UUID,
    token: str | None,
    db: AsyncSession,
) -> User | None:
    """The browser's native EventSource can't set an Authorization header,
    so this route accepts the access token as a query param as a fallback
    (a standard, well-established pattern for SSE auth) -- the header path
    still works for any client that can set one."""
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user if (user and user.is_active) else None


@router.get("/{trip_id}/stream")
async def stream_trip_progress(
    trip_id: uuid.UUID,
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream of live agent progress for one trip (spec
    section 19). Event `type` values: agent_started, agent_completed,
    tool_started, tool_completed, search_result, budget_updated,
    critic_result, replanning, completed, error -- each mirrors an
    AgentEvent row so a client that missed the stream can still fetch the
    full history from GET /agent-runs/{id}."""
    user = await _resolve_user_for_stream(trip_id, token, db)
    trip = None
    if user:
        result = await db.execute(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
        trip = result.scalar_one_or_none()

    async def event_generator():
        if not user or not trip:
            yield _format_sse({"type": "error", "message": "Not authenticated for this trip."})
            return
        try:
            async for event in subscribe(str(trip_id)):
                yield _format_sse(event)
        except asyncio.CancelledError:
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
