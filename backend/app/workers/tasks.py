import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import get_settings
from app.models.trip import Trip
from app.services.trip_service import TripService
from app.workers.celery_app import celery_app

async def _run(trip_id: str, coro_name: str, celery_task_id: str | None, *args):
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, future=True)  # fresh per task, always
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as db:
            trip = await db.get(Trip, uuid.UUID(trip_id))
            service = TripService(settings)
            await getattr(service, coro_name)(db, trip, *args, celery_task_id=celery_task_id)
    finally:
        await engine.dispose()

@celery_app.task(name="trip_planner.plan", bind=True, max_retries=2, default_retry_delay=5)
def plan_trip_task(self, trip_id: str, message: str, resume: bool):
    try:
        asyncio.run(_run(trip_id, "continue_trip" if resume else "plan_existing_trip", self.request.id, message))
    except Exception as exc:
        raise self.retry(exc=exc)

@celery_app.task(name="trip_planner.modify", bind=True, max_retries=1)
def modify_trip_task(self, trip_id: str, message: str):
    try:
        asyncio.run(_run(trip_id, "modify_trip", self.request.id, message))
    except Exception as exc:
        raise self.retry(exc=exc)

@celery_app.task(name="trip_planner.regenerate", bind=True, max_retries=1)
def regenerate_trip_task(self, trip_id: str):
    try:
        asyncio.run(_run(trip_id, "regenerate_trip", self.request.id))
    except Exception as exc:
        raise self.retry(exc=exc)
