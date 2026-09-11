# Design decisions

The non-obvious architectural choices in this project and why they exist.
Written for someone reading the code for the first time (including
interviewers).

## Why a scheduler hub instead of static graph edges

The LangGraph graph uses a **central scheduler node** rather than
hard-wired edges between agents. Every agent node routes back to
`scheduler`, which inspects the dependency table and fires all agents
whose prerequisites are now satisfied — via `langgraph.types.Send` for
dynamic dispatch.

**Why:** Static edges can't express "run flight_research and
hotel_research in parallel, but only after destination_research finishes."
You'd need fan-out/fan-in combinators, which LangGraph supports but which
become unmaintainable with 14 nodes and cross-branch dependencies. The
scheduler pattern makes the dependency graph a single Python dict
(`state.py → DEPENDENCIES`) that's trivially readable and testable.

**Trade-off:** Every node round-trips through `scheduler`, adding one
extra "hop" per transition. In practice this is ~0ms since `scheduler` is
pure Python with no I/O. The clarity gain is worth it.

## Why mock providers are first-class, not afterthoughts

Every external data source (flights, hotels, places, food, weather,
currency) has a `base.py` abstract interface and a `mock.py`
implementation that returns deterministic, realistic data. The mock path
is what's tested in CI and what runs in `DEMO_MODE=true`.

**Why:** This project needs to demonstrate the **agentic workflow**, not
the ability to call the Amadeus API. By making mocks the default, the
entire pipeline — including the critic catching budget overruns and
triggering partial replanning — runs reproducibly without any API key,
any network access, or any paid service. An interviewer can clone the
repo, run `docker compose up`, and see the full system work in 30 seconds.

**Trade-off:** Real provider adapters exist but aren't battle-tested
against live APIs. This is documented honestly in
`docs/future-improvements.md`.

## Why Redis pub/sub + SSE instead of WebSockets

Agent progress is streamed to the browser via **Server-Sent Events
(SSE)**, with the backend publishing events to Redis pub/sub and the SSE
endpoint subscribing to the trip's channel.

**Why:**
1. SSE is unidirectional (server → client), which is exactly what
   progress streaming needs. WebSockets add bidirectional complexity for
   no benefit here.
2. Redis pub/sub decouples the worker (which may be a Celery process on
   a different machine) from the API server that holds the SSE connection.
   The worker publishes; the API server subscribes. No shared memory
   needed.
3. SSE auto-reconnects natively in the browser via `EventSource`. With
   WebSockets you'd need manual reconnection logic.

**Trade-off:** SSE doesn't support binary data or client-to-server
messages. Neither is needed here — trip modifications go through REST
endpoints.

## Why the critic is a separate node, not a conditional check

The critic is a dedicated graph node that receives the fully assembled
itinerary and evaluates it against a structured checklist (budget
overrun, day packing, preference violations, missing activities). If it
rejects the plan, it specifies which upstream agents need to rerun.

**Why:** Making the critic a separate node means:
1. It has its own prompt and its own LLM call, not a bolted-on "is this
   good?" check at the end of the itinerary generator. This separation
   means the critic can be honest — it's not evaluating its own work.
2. It produces structured output (`approved: bool`,
   `issues: list[str]`, `replan_targets: list[str]`) that the replanner
   can act on programmatically.
3. It can be tested independently — the test suite includes cases where
   the critic correctly rejects a budget overrun and cases where it
   correctly approves a valid plan.

**Trade-off:** An extra LLM call per iteration. The `MAX_AGENT_ITERATIONS`
cap (default: 3) bounds the cost.

## Why the completed_nodes reducer uses a __RESET__ sentinel

The `merge_completed` reducer in `state.py` uses a `["__RESET__", ...]`
sentinel to replace the completed set rather than merge into it. This is
how partial replanning works: the scheduler computes which nodes need to
rerun, then sends `["__RESET__"] + nodes_to_keep` to wipe the affected
nodes from the completed set without losing the unaffected ones.

**Why:** LangGraph reducers are always additive — you can't "remove" a
value from an `Annotated[list, operator.add]` field. The sentinel
pattern gives us subtraction semantics within the additive framework
without requiring a custom LangGraph channel.

**Why this matters:** This is the mechanism that makes partial replanning
real. Without it, a rejected plan would have to restart the entire graph
from scratch. With it, only the affected nodes rerun — and this is tested
with a real captured example in `docs/agent-architecture.md`.

## Why asyncio background tasks AND Celery

The project supports two background execution modes via the
`BACKGROUND_EXECUTOR` setting:

- `fastapi` (default for local dev): uses `asyncio.create_task()` — zero
  infrastructure, starts instantly.
- `celery` (default in Docker Compose): uses a real Celery worker with
  Redis as the broker.

**Why both:** During development, you don't want to run a Celery worker
just to test a prompt. In production, you need Celery for horizontal
scaling, task retries (`task_acks_late=True`), and crash recovery. The
`_dispatch_background` helper in `trips.py` abstracts the choice to a
single `if/else`.

## Why a multi-provider LLM pool with daily caps

The `LLM_PROVIDER_CHAIN` setting accepts a list of providers (e.g.,
`["google", "openrouter", "groq"]`). The system tries each in order and
falls back to the next if a provider hits its daily cap
(`LLM_DAILY_CAP_*`).

**Why:** Free-tier API keys have aggressive rate limits. By rotating
across providers, the project can run real LLM calls sustainably without
paying for a single API subscription. This is a practical solution for a
portfolio project that needs to be demoable at any time.
