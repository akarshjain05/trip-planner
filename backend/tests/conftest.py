"""
Shared fixtures.

Tests run against a REAL Postgres database (trip_planner_test), not
SQLite -- several models use JSONB and the app is designed for Postgres,
so testing against anything else would mask real bugs (this bit us once
already during manual testing: a `Date` column silently expects real
`date` objects via asyncpg, which SQLite's looser typing wouldn't catch).

Each test gets its OWN async engine (function-scoped), created and
disposed inside that test's own event loop. Sharing one module-level
engine across tests looked simpler but breaks under pytest-asyncio's
per-test event loops -- asyncpg connections get bound to whichever loop
first used them and raise "attached to a different loop" once a later
test's loop tries to reuse them. Schema setup runs once, synchronously,
via its own throwaway event loop at import time -- before pytest-asyncio
creates any per-test loop -- so it can't collide with one either.

DEMO_MODE=true / LLM_PROVIDER=mock for the whole suite so it runs with
zero external API calls or keys, per spec section 27/28.
"""
from __future__ import annotations

import asyncio
import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://trip_planner:trip_planner_dev@localhost:5432/trip_planner_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("LLM_PROVIDER", "mock")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

get_settings.cache_clear()
settings = get_settings()


def _reset_schema_sync() -> None:
    async def _reset():
        import app.models  # noqa: registers all tables on Base.metadata
        from app.db.base import Base

        engine = create_async_engine(settings.DATABASE_URL, future=True)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_reset())


_reset_schema_sync()


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    session_local = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_local() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _rebind_background_task_session():
    """Background planning tasks (fire-and-forget from the /plan and
    /modify routes, and every agent node's progress emit()) go through
    app.db.session.AsyncSessionLocal directly, not the FastAPI get_db
    dependency -- so overriding get_db alone doesn't reach them. That
    module-level session factory is created once at import time and binds
    to whichever event loop is running then; under pytest-asyncio's
    per-test event loops, reusing it in a later test's loop raises "Future
    attached to a different loop". Rebinding it fresh at the start of
    every test fixes this in the test environment; in the real (single
    long-lived event loop) process this rebind never runs at all."""
    import app.db.session as session_module

    new_engine = create_async_engine(settings.DATABASE_URL, future=True)
    session_module.engine = new_engine
    session_module.AsyncSessionLocal = async_sessionmaker(
        bind=new_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False,
    )

    from app.tools import cache as cache_module

    cache_module._redis_client = None  # same rebind story for the Redis client singleton

    yield
    await new_engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    from app.db.session import get_db
    from app.main import app

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def registered_user(client):
    email = f"test-{uuid.uuid4().hex[:10]}@example.com"
    resp = await client.post("/api/auth/register", json={"email": email, "password": "testpass123", "full_name": "Test User"})
    assert resp.status_code == 201, resp.text
    tokens = resp.json()
    return {"email": email, "headers": {"Authorization": f"Bearer {tokens['access_token']}"}}
