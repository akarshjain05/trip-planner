# Architecture

## System overview

```mermaid
flowchart LR
    subgraph Client
        FE[React + Vite frontend]
    end
    subgraph Server["FastAPI backend"]
        API[REST routes]
        SVC[TripService]
        GRAPH[LangGraph agent graph]
        BG[asyncio background task]
    end
    DB[(PostgreSQL)]
    CACHE[(Redis)]

    FE -- "REST (JWT)" --> API
    FE -- "SSE /trips/{id}/stream" --> API
    API --> SVC
    SVC -- "spawns" --> BG
    BG --> GRAPH
    GRAPH -- "tool calls, cache" --> CACHE
    GRAPH -- "progress events" --> CACHE
    CACHE -- "pub/sub" --> API
    SVC -- "reads/writes" --> DB
```

## Request flow

1. `POST /api/trips` creates a `Trip` row (`status=draft`) with the user's
   raw prompt. Fast, synchronous.
2. `POST /api/trips/{id}/plan` flips the trip to `planning` and returns
   `202 Accepted` immediately — the actual graph run happens in a
   background asyncio task (see below), not inline in the request. This
   matters: if planning ran synchronously inside the request handler, the
   frontend could never observe live progress, because by the time it got
   a response and opened the SSE connection, everything would already have
   happened.
3. The frontend opens `GET /api/trips/{id}/stream` (SSE) and polls
   `GET /api/trips/{id}/status` as a fallback/completion signal.
4. Every agent node calls a shared `emit()` helper
   (`app/services/progress.py`) at key points. Each call does two things:
   writes an `AgentEvent` row (durable history, replayable via
   `GET /agent-runs/{id}`) and publishes the same payload to a Redis
   pub/sub channel keyed by trip ID, which the SSE endpoint subscribes to.
5. When the graph run finishes (approved, or the iteration cap is hit),
   `TripService._sync_state_to_db` writes the final `TripState` into
   normalized Postgres tables (drops and recreates the regenerable
   research/itinerary rows — trips are small enough that this is simpler
   and safer than diffing) and stores the *raw* state as JSONB on the
   `Trip` row itself, so a later request (answering a clarifying question,
   or a "make it cheaper" modification) can reconstruct exactly where the
   run left off.

## Background execution

The app natively uses **Celery + Redis** to dispatch and process long-running itinerary generation tasks asynchronously across distributed workers.

- The API endpoints (e.g. `POST /trips`) dispatch a task via `celery_app.send_task()` and return immediately.
- The dedicated `worker` container picks up the task and runs the LangGraph orchestrator.
- Progress and completion are observable via Redis pub/sub (live via Server-Sent Events) and Postgres (durable).
- To prevent duplicate work (idempotency), every agent execution is tracked with a unique `agent_run_id` which is verified before committing final itineraries to the database.

For local development without Docker, `BACKGROUND_EXECUTOR="asyncio"` can be set in `.env` to fall back to `asyncio.create_task()` within the FastAPI process, completely bypassing the need for a standalone Celery worker while keeping the exact same pub/sub event semantics.

## Where LangGraph's checkpointer is (and isn't) used

The compiled graph uses `MemorySaver` — in-process checkpointing that
lets LangGraph's own execution model work correctly (superstep
scheduling, fan-out/fan-in) *within* a single `ainvoke()` call. It is
**not** relied on for cross-request resumption. That responsibility is
explicit and in application code instead: `Trip.state_snapshot` (a JSONB
column) holds the last full `TripState`, and every new planning
invocation — resuming after a clarifying question, or a user-driven
partial replan — reconstructs its starting state from that column before
calling the graph again. This was a deliberate choice for
predictability: cross-process checkpointer persistence has its own
subtleties (serialization, thread-ID semantics across restarts), and
since the app already needs normalized Postgres tables for querying,
keeping *one* source of truth for "what does this trip's plan currently
look like" was simpler to reason about and test than depending on two.

## Caching

Every tool-provider call (flights, hotels, places, weather) goes through
`app/tools/cache.py`, a thin Redis-backed cache keyed by a hash of the
call's arguments, with per-category TTLs from `.env`. This was verified
against a real local Redis instance during development (see
`backend/tests/test_tools.py::TestCache`).
