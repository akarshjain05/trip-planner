from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.trip import Trip
from app.models.user import User
from app.schemas.agent import AgentRunRead

router = APIRouter(prefix="/agent-runs", tags=["agent-runs"])


@router.get("/{run_id}", response_model=AgentRunRead)
async def get_agent_run(
    run_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentRun:
    result = await db.execute(
        select(AgentRun)
        .join(Trip, AgentRun.trip_id == Trip.id)
        .where(AgentRun.id == run_id, Trip.user_id == current_user.id)
        .options(selectinload(AgentRun.events))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agent run not found.")
    return run
