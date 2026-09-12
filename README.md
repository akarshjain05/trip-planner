# Wayfarer — Agentic AI Trip Planner

[![Tests](https://github.com/akarshjain05/trip-planner/actions/workflows/test.yml/badge.svg)](https://github.com/akarshjain05/trip-planner/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev)

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

```mermaid
graph LR
    classDef default fill:#1a1a2e,stroke:#2b2b40,stroke-width:1px,color:#a5a5b4
    classDef startNode fill:#0d233a,stroke:#1a4b77,stroke-width:2px,color:#64b5f6,rx:10,ry:10
    classDef parallelNode fill:#152b22,stroke:#1e503a,stroke-width:2px,color:#4db6ac,rx:8,ry:8
    classDef assembleNode fill:#231a3a,stroke:#4a327a,stroke-width:2px,color:#b39ddb,rx:8,ry:8
    classDef criticNode fill:#3a2a0d,stroke:#77521a,stroke-width:2px,color:#ffb74d,rx:15,ry:15
    classDef errorNode fill:#3a1414,stroke:#7a2424,stroke-width:2px,color:#e57373,rx:8,ry:8
    
    req[Extract Requirements]:::startNode --> dest[Research Destination]:::startNode
    
    dest --> flights[Rank Flights]:::parallelNode
    dest --> hotels[Rank Hotels]:::parallelNode
    
    flights --> places[Rank Places]:::parallelNode
    hotels --> food[Rank Food]:::parallelNode
    
    places --> trans[Plan Transportation]:::assembleNode
    food --> trans
    
    trans --> weather[Weather Outlook]:::assembleNode
    weather --> budget[Optimize Budget]:::assembleNode
    budget --> itin[Generate Itinerary]:::assembleNode
    
    itin --> critic{Critic Review}:::criticNode
    
    critic -->|Approved| done([Final Itinerary]):::startNode
    critic -->|Rejected| replan[Targeted Replanner]:::errorNode
    
    replan -.->|Re-runs only affected agents| flights
    replan -.-> hotels
```

See [`docs/agent-architecture.md`](docs/agent-architecture.md) for the full
graph, the critic's checklist, and how partial replanning actually works
(with a real captured example of the loop catching and fixing two
different problems in the same run).

## Key features

- **Multi-agent LangGraph workflow** with parallel research branches,
  a dedicated critic node, and partial replanning via the `Send` API
- **Live SSE streaming** — watch every agent start, think, and complete
  in the browser in real time
- **JWT auth** — secure email/password authentication
- **Drag-and-drop itinerary reordering** — `@dnd-kit` with backend
  persistence
- **Framer Motion animations** — page transitions, agent status
  animations, staggered list renders
- **Admin dashboard** — token usage, cost tracking, iteration counts
- **Dark / light theme** with `localStorage` persistence
- **Rate limiting** — SlowAPI middleware on planning endpoints
- **Celery workers** — real distributed task queue in Docker, with an
  asyncio fallback for local dev
- **OpenTelemetry tracing** — every LangGraph node is instrumented,
  exported to Jaeger
- **Multi-LLM provider abstraction** — NVIDIA / OpenRouter / Groq / Google with rule-based fallback
- **Full demo mode** — the entire agentic pipeline runs without any API
  key (`DEMO_MODE=true`)

## Quickstart

```bash
git clone <this-repo> ai-trip-planner && cd ai-trip-planner
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend docs (OpenAPI): http://localhost:8000/docs
- Jaeger traces: http://localhost:16686
- Flower (Celery monitoring): http://localhost:5555
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
| [`docs/design-decisions.md`](docs/design-decisions.md) | Why we made the non-obvious choices |
| [`docs/database.md`](docs/database.md) | Schema and design choices |
| [`docs/api.md`](docs/api.md) | REST endpoints |
| [`docs/setup.md`](docs/setup.md) | Local dev without Docker, port config |
| [`docs/environment-variables.md`](docs/environment-variables.md) | Every setting, explained |
| [`docs/providers.md`](docs/providers.md) | Mock vs. real provider adapters, how to switch |
| [`docs/security.md`](docs/security.md) | Auth, secrets, SSRF/XSS/CORS posture |
| [`docs/deployment.md`](docs/deployment.md) | Docker Compose, production notes |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common issues |
| [`docs/future-improvements.md`](docs/future-improvements.md) | What's completed and what's genuinely out of scope |
| [`docs/sample-sse-trace.md`](docs/sample-sse-trace.md) | A real captured live-progress trace |

## Tech stack

**Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async),
PostgreSQL, Redis, Alembic, Celery, LangGraph, LangChain, OpenTelemetry,
JWT auth, SlowAPI.
**Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, TanStack Query,
Zustand, React Router, Recharts, Framer Motion, dnd-kit.
**Infra:** Docker Compose, Jaeger, Flower, pytest, Playwright.

## Tests

```bash
# Backend — 64 unit/integration tests against real Postgres + Redis
cd backend
python -m pytest tests/ -v

# Frontend — Playwright E2E (requires the app to be running)
cd frontend
npx playwright test
```

**Backend (64 tests):** real Postgres + Redis, zero external API calls.
Covers: the mock reasoning layer (requirement extraction, ranking, budget
optimization, critic logic, modification interpretation), the graph's
topology and a documented LangGraph fan-in bug this project ran into and
fixed, full end-to-end planning runs (including a genuinely-impossible
budget to prove the iteration cap and honest-failure path both work),
Celery task dispatch, auth, and the full trip API through real HTTP + DB.

**Frontend (2 E2E specs):** Playwright tests covering the full
registration → login → trip creation → SSE streaming → itinerary display
flow.

## License

MIT — see [`LICENSE`](LICENSE).
