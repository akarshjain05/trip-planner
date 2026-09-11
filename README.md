# Wayfarer — Agentic AI Trip Planner

An AI travel planner built as a genuine **multi-agent LangGraph workflow**,
not a single prompt pretending to be one. Describe a trip in plain
language; a chain of specialized agents extracts your requirements,
researches destinations/flights/hotels/places/food in parallel, builds a
transportation and weather picture, assembles a costed day-by-day
itinerary, and hands it to a critic that can send the whole thing back for
targeted rework — before you ever see it.

```
"I want to visit Japan for 8 days in October. My budget is ₹1,50,000.
 I like nature, anime, food and photography. I don't like crowded
 tourist attractions. I am traveling with one friend. I prefer
 comfortable hotels and don't want extremely long travel days."
```
↓ becomes a full itinerary, live-streamed to the browser as it's built.

## Why this is agentic, not a wrapper

The output of every stage is the structured, typed input to the next —
there is no single call that hallucinates an entire trip:

```
requirements → destination →  ┬─ flights ──→ places ─┬→ transportation
                               └─ hotels ───→ food ───┘        ↓
                                                          weather → budget
                                                                    ↓
                                                            itinerary → critic
                                                                          │
                                              ┌───────────────────────────┘
                                              ↓ rejected
                                          replanner → (only the affected
                                                        agents re-run)
```

See [`docs/agent-architecture.md`](docs/agent-architecture.md) for the full
graph, the critic's checklist, and how partial replanning actually works
(with a real captured example of the loop catching and fixing two
different problems in the same run).

## What's real here — and what's honestly scoped down

This is a large spec. Rather than fake breadth across all of it, here's
exactly what's genuine and tested versus simplified:

**Fully built, tested for real (not against mocks-of-mocks — a real local
Postgres, a real local Redis, a real HTTP server):**
- The LangGraph agent graph, including the parallel research branches and
  the critic → replanning loop with real backward routing and a hard
  iteration cap
- FastAPI + SQLAlchemy 2 + PostgreSQL, with Alembic migrations that apply
  and roll back cleanly
- JWT auth, trip CRUD, live SSE progress streaming
- Mock providers for flights/hotels/places/food/weather/currency — clearly
  labeled, deterministic, zero paid keys required (`DEMO_MODE=true`)
- A multi-LLM-provider abstraction (OpenAI/Anthropic/Google/Groq/OpenRouter)
  with a rule-based fallback so the *entire* graph — including the critic
  loop — runs and is unit-tested without any LLM key at all
- React/TypeScript/Vite/Tailwind frontend that builds cleanly, with a live
  agent-progress view, itinerary, and budget dashboard
- **70 automated backend tests**, all passing — see `backend/tests/`

**Deliberately simplified, documented rather than hidden:**
- Celery → asyncio background tasks + Redis pub/sub (the spec allows an
  "equivalent" background-job system; see
  [`docs/architecture.md`](docs/architecture.md#background-execution))
- Real flight/hotel/weather/currency/search adapters have clean interfaces
  and are wired into the provider factory, but aren't live-tested — this
  sandbox has no network egress to those APIs. The mock path is what's
  proven; see [`docs/providers.md`](docs/providers.md)
- Docker Compose is written and YAML-validated but not run end-to-end here
  (no Docker-in-Docker in the build environment) — everything it wraps
  (backend, migrations, tests, frontend build) *is* independently verified
- No OAuth social login, no admin/observability page, lighter animation
  than a full Framer Motion treatment, no drag-and-drop reordering — noted
  as follow-ups in [`docs/future-improvements.md`](docs/future-improvements.md)

## Quickstart

```bash
git clone <this-repo> ai-trip-planner && cd ai-trip-planner
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend docs (OpenAPI): http://localhost:8000/docs
- Nothing above needs an API key — `DEMO_MODE=true` by default.

Running multiple projects locally and hitting port collisions? Every port
is overridable — see [`docs/setup.md`](docs/setup.md#port-collisions).

For running without Docker (e.g. for development), see
[`docs/setup.md`](docs/setup.md).

## Docs

| Doc | Covers |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System overview, request flow, background execution |
| [`docs/agent-architecture.md`](docs/agent-architecture.md) | The LangGraph graph, state, critic, replanning |
| [`docs/database.md`](docs/database.md) | Schema and design choices |
| [`docs/api.md`](docs/api.md) | REST endpoints |
| [`docs/setup.md`](docs/setup.md) | Local dev without Docker, port config |
| [`docs/environment-variables.md`](docs/environment-variables.md) | Every setting, explained |
| [`docs/providers.md`](docs/providers.md) | Mock vs. real provider adapters, how to switch |
| [`docs/security.md`](docs/security.md) | Auth, secrets, SSRF/XSS/CORS posture |
| [`docs/deployment.md`](docs/deployment.md) | Docker Compose, production notes |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common issues |
| [`docs/future-improvements.md`](docs/future-improvements.md) | What's deliberately out of scope |
| [`docs/sample-sse-trace.md`](docs/sample-sse-trace.md) | A real captured live-progress trace |

## Tech stack

**Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async),
PostgreSQL, Redis, Alembic, LangGraph, LangChain, JWT auth.
**Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query,
Zustand, React Router, Recharts.
**Infra:** Docker Compose, pytest (70 tests against real Postgres/Redis).

## Tests

```bash
cd backend
python -m pytest tests/ -v
```

70 tests, real Postgres + Redis, zero external API calls. Covers: the
mock reasoning layer (requirement extraction, ranking, budget
optimization, critic logic, modification interpretation), the graph's
topology and a documented LangGraph fan-in bug this project ran into and
fixed, full end-to-end planning runs (including a genuinely-impossible
budget to prove the iteration cap and honest-failure path both work),
auth, and the full trip API through real HTTP + DB.

## License

MIT — see [`LICENSE`](LICENSE).
