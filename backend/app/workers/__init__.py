"""
Background planning execution.

The spec calls for "Celery or an equivalent background-job system." This
build uses asyncio background tasks + Redis pub/sub instead of a literal
Celery worker -- see docs/architecture.md#background-execution for the
full reasoning. In short: a real Celery deployment needs a broker, a
result backend, and worker process management, which is genuine
operational complexity this single-container demo app doesn't need to
take on to demonstrate the actual agentic workflow.

The actual background-task dispatch lives at the call site
(`asyncio.create_task(...)` in app/api/routes/trips.py) rather than here,
because FastAPI's request-scoped dependencies (the current user, the
per-request DB session) are most naturally captured in a closure right
where the route already has them. This module is the documented,
findable answer to "where would I plug in Celery instead" -- nothing
here is imported by the app as shipped; wrap TripService's methods in
@celery_app.task if you outgrow asyncio background tasks.

Example sketch (not wired up):

    from celery import Celery
    celery_app = Celery("trip_planner", broker=settings.REDIS_URL)

    @celery_app.task
    def plan_trip_task(trip_id: str, message: str) -> None:
        asyncio.run(_plan_trip_async(trip_id, message))

    async def _plan_trip_async(trip_id: str, message: str) -> None:
        async with AsyncSessionLocal() as db:
            trip = await db.get(Trip, trip_id)
            await TripService(get_settings()).plan_existing_trip(db, trip, message)

Progress would publish to Redis exactly the same way it does today
(app/services/progress.py doesn't know or care whether it's being called
from an asyncio task or a Celery worker), so the frontend's SSE
consumption wouldn't need to change at all.
"""
