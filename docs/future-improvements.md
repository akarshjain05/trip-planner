# Future improvements

Honest list of what remains genuinely out of scope in this build, and what
was completed after the initial design pass.

## Completed since the initial build

These items were originally scoped down but have since been fully
implemented and tested:

- **Real Celery workers** — `app/workers/celery_app.py` with a dedicated
  `worker` service in `docker-compose.yml`. The `BACKGROUND_EXECUTOR`
  setting switches between asyncio (dev) and Celery (production) at
  runtime.
- **Drag-and-drop itinerary reordering** — `@dnd-kit/sortable` in
  `ItineraryDayCard.tsx` with a `PUT` endpoint that persists the new
  `order_index` per day.
- **Framer Motion polish** — `AnimatePresence` page transitions in
  `App.tsx`, animated agent status messages in `AgentProgressBoard.tsx`,
  staggered list animations in `TripsListPage.tsx`.
- **Admin / observability dashboard** — `AdminDashboardPage.tsx` surfacing
  token usage, cost, iteration counts, and tool-call counts from
  `agent_runs`.
- **Dark / light theme toggle** — theme store with `localStorage`
  persistence and a toggle in the NavBar.
- **Rate limiting** — SlowAPI middleware with per-endpoint limits
  (`app/core/limiter.py`), applied to planning and modification endpoints.
- **Fine-grained replanning via the Send API** — `scheduler.py` uses
  `langgraph.types.Send` for dynamic per-node dispatch with dependency-
  aware routing, skipping unaffected branches entirely.
- **OpenTelemetry tracing** — FastAPI and every LangGraph node are
  instrumented with OTEL spans, exported to a Jaeger instance in
  `docker-compose.yml`.
- **Playwright E2E tests** — `tests/auth.spec.ts` and
  `tests/planning.spec.ts` covering the full user journey, with a CI job
  in `.github/workflows/test.yml`.
- **Fully wired OAuth / social login** — `app/api/routes/oauth.py` integrates with Google OAuth via Authlib, handles user creation, and seamlessly redirects to the frontend `OAuthCallbackPage` for token injection.

## Still genuinely out of scope

- **Live verification of real provider adapters** (Amadeus, Google
  Places, Tavily, etc.) against actual APIs — the mock path is what's
  proven end-to-end. Weather (Open-Meteo) and currency
  (Frankfurter.app) need no key and are the fastest to verify yourself.
- **Full WCAG accessibility audit.** Semantic HTML and focus states are
  used throughout, but this hasn't had a dedicated accessibility pass
  (screen-reader testing, full keyboard-nav audit, contrast verification
  beyond the obvious).
- **Real per-run cost/tool-call/time enforcement.** `MAX_LLM_COST_USD`,
  `MAX_TOOL_CALLS`, and `MAX_TRIP_PLANNING_TIME_SECONDS` are read into
  settings and tracked in the scheduler node, but only
  `MAX_AGENT_ITERATIONS` actually gates graph execution today. The
  scheduler checks all three limits and returns an error state, but this
  hasn't been integration-tested under real load.
