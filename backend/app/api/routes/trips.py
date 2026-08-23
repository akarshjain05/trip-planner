from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.session as db_session_module
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.itinerary import Itinerary
from app.models.research import ResearchSource
from app.models.trip import Trip, TripFeedback, TripStatus
from app.models.user import User
from app.schemas.agent import AgentRunRead, ResearchSourceRead
from app.schemas.itinerary import BudgetLineRead, BudgetRead, ItineraryRead
from app.schemas.trip import TripCreate, TripModify, TripRead, TripStatusRead
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["trips"])


async def _get_owned_trip(trip_id: uuid.UUID, db: AsyncSession, user: User) -> Trip:
    result = await db.execute(select(Trip).where(Trip.id == trip_id, Trip.user_id == user.id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Trip not found.")
    return trip


def _run_in_background(coro_factory) -> None:
    """Fire-and-forget a planning run in its own DB session/task -- this is
    the asyncio-based stand-in for a Celery worker (see docs/architecture.md
    for the trade-off). The request returns immediately; progress streams
    over SSE at GET /trips/{id}/stream."""
    asyncio.create_task(coro_factory())


@router.post("", response_model=TripRead, status_code=status.HTTP_201_CREATED)
async def create_trip(
    payload: TripCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Trip:
    trip = Trip(
        user_id=current_user.id, title=payload.prompt[:80] or "Untitled trip",
        status=TripStatus.DRAFT, original_prompt=payload.prompt, state_snapshot={},
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)
    return trip


@router.get("", response_model=list[TripRead])
async def list_trips(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[Trip]:
    result = await db.execute(select(Trip).where(Trip.user_id == current_user.id).order_by(Trip.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{trip_id}", response_model=TripRead)
async def get_trip(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Trip:
    return await _get_owned_trip(trip_id, db, current_user)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_trip(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    trip = await _get_owned_trip(trip_id, db, current_user)
    await db.delete(trip)
    await db.commit()


@router.post("/{trip_id}/plan", response_model=TripStatusRead, status_code=status.HTTP_202_ACCEPTED)
async def plan_trip(
    trip_id: uuid.UUID, payload: TripModify | None = None,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> TripStatusRead:
    """Kicks off planning in the background. If the trip is awaiting a
    clarifying answer, `payload.message` is treated as that answer and the
    graph resumes from requirement_extractor; otherwise it's the initial
    planning run using the trip's original prompt."""
    trip = await _get_owned_trip(trip_id, db, current_user)
    if trip.status == TripStatus.PLANNING:
        raise HTTPException(status.HTTP_409_CONFLICT, "This trip is already being planned.")

    is_resume = trip.status == TripStatus.AWAITING_INPUT
    message = (payload.message if payload else None) or trip.original_prompt
    trip.status = TripStatus.PLANNING
    await db.commit()

    async def _do_run():
        service = TripService(get_settings())
        async with db_session_module.AsyncSessionLocal() as bg_db:
            bg_trip = await _get_owned_trip(trip_id, bg_db, current_user)
            if is_resume:
                await service.continue_trip(bg_db, bg_trip, message)
            else:
                await service.plan_existing_trip(bg_db, bg_trip, message)

    _run_in_background(_do_run)
    return TripStatusRead(trip_id=trip.id, status=trip.status, awaiting_input=False)


@router.post("/{trip_id}/modify", response_model=TripStatusRead, status_code=status.HTTP_202_ACCEPTED)
async def modify_trip(
    trip_id: uuid.UUID, payload: TripModify,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> TripStatusRead:
    trip = await _get_owned_trip(trip_id, db, current_user)
    if trip.status not in (TripStatus.COMPLETED, TripStatus.AWAITING_INPUT):
        raise HTTPException(status.HTTP_409_CONFLICT, "Trip has no itinerary yet to modify.")
    trip.status = TripStatus.PLANNING
    await db.commit()

    async def _do_modify():
        service = TripService(get_settings())
        async with db_session_module.AsyncSessionLocal() as bg_db:
            bg_trip = await _get_owned_trip(trip_id, bg_db, current_user)
            await service.modify_trip(bg_db, bg_trip, payload.message)

    _run_in_background(_do_modify)
    return TripStatusRead(trip_id=trip.id, status=trip.status, awaiting_input=False)


@router.post("/{trip_id}/regenerate", response_model=TripStatusRead, status_code=status.HTTP_202_ACCEPTED)
async def regenerate_trip(
    trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> TripStatusRead:
    trip = await _get_owned_trip(trip_id, db, current_user)
    trip.status = TripStatus.PLANNING
    await db.commit()

    async def _do_regenerate():
        service = TripService(get_settings())
        async with db_session_module.AsyncSessionLocal() as bg_db:
            bg_trip = await _get_owned_trip(trip_id, bg_db, current_user)
            await service.regenerate_trip(bg_db, bg_trip)

    _run_in_background(_do_regenerate)
    return TripStatusRead(trip_id=trip.id, status=trip.status, awaiting_input=False)


@router.post("/{trip_id}/feedback", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    trip_id: uuid.UUID, payload: TripModify,
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> dict:
    trip = await _get_owned_trip(trip_id, db, current_user)
    db.add(TripFeedback(trip_id=trip.id, message=payload.message, interpreted_changes={}, nodes_rerun=[]))
    await db.commit()
    return {"status": "recorded"}


@router.get("/{trip_id}/status", response_model=TripStatusRead)
async def trip_status(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> TripStatusRead:
    trip = await _get_owned_trip(trip_id, db, current_user)
    snapshot = trip.state_snapshot or {}
    result = await db.execute(
        select(AgentRun).where(AgentRun.trip_id == trip.id).order_by(AgentRun.created_at.desc()).limit(1)
    )
    latest_run = result.scalar_one_or_none()
    return TripStatusRead(
        trip_id=trip.id, status=trip.status,
        latest_agent_run_id=latest_run.id if latest_run else None,
        awaiting_input=trip.status == TripStatus.AWAITING_INPUT,
        clarifying_question=(snapshot.get("missing_info") or {}).get("clarifying_question")
        if trip.status == TripStatus.AWAITING_INPUT else None,
    )


@router.get("/{trip_id}/itinerary", response_model=ItineraryRead)
async def get_itinerary(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> Itinerary:
    trip = await _get_owned_trip(trip_id, db, current_user)
    result = await db.execute(
        select(Itinerary).where(Itinerary.trip_id == trip.id).order_by(Itinerary.version.desc()).limit(1)
    )
    itinerary = result.scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No itinerary generated yet.")
    await db.refresh(itinerary, attribute_names=["days"])
    for day in itinerary.days:
        await db.refresh(day, attribute_names=["activities"])
    return itinerary


@router.get("/{trip_id}/budget", response_model=BudgetRead)
async def get_budget(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> BudgetRead:
    trip = await _get_owned_trip(trip_id, db, current_user)
    result = await db.execute(
        select(Itinerary).where(Itinerary.trip_id == trip.id).order_by(Itinerary.version.desc()).limit(1)
    )
    itinerary = result.scalar_one_or_none()
    if not itinerary:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No budget available yet.")
    await db.refresh(itinerary, attribute_names=["budget_lines"])

    total_budget = (trip.state_snapshot or {}).get("requirements", {}).get("budget_amount")
    return BudgetRead(
        total_budget=total_budget, currency=itinerary.currency,
        lines=[BudgetLineRead.model_validate(l) for l in itinerary.budget_lines],
        total_estimated=itinerary.total_estimated_cost or 0.0,
        remaining=(total_budget - itinerary.total_estimated_cost) if (total_budget and itinerary.total_estimated_cost is not None) else None,
    )


@router.get("/{trip_id}/sources", response_model=list[ResearchSourceRead])
async def get_sources(trip_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> list[ResearchSource]:
    trip = await _get_owned_trip(trip_id, db, current_user)
    result = await db.execute(
        select(ResearchSource).join(AgentRun, ResearchSource.agent_run_id == AgentRun.id).where(AgentRun.trip_id == trip.id)
    )
    return list(result.scalars().all())
