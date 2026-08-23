# Future improvements

Honest list of what's out of scope in this build, roughly ordered by how
much it'd matter for a real deployment.

## Scoped down for time, not forgotten

- **Real Celery workers** in place of the current asyncio-background-task
  execution, for horizontal scaling of planning throughput. The seam is
  already there — see `docs/architecture.md#background-execution`.
- **Live verification of the real provider adapters** (Amadeus, Google
  Places, Tavily, etc.) against actual APIs — written to each provider's
  documented contract but not exercised against a live endpoint in this
  build environment (no network egress to them here). Weather
  (Open-Meteo) and currency (Frankfurter.app) need no key and are the
  fastest to verify yourself.
- **OAuth / social login.** The auth system is structured so a provider
  could be added alongside email/password (a new `AuthProvider` concept
  next to `User`), but only email/password is implemented.
- **Drag-and-drop itinerary reordering** in the frontend. The activity
  model has an `order_index` column ready for it; the UI doesn't expose
  reordering yet.
- **Framer Motion polish.** The frontend uses plain CSS transitions
  rather than the full choreographed-animation treatment — functional and
  consistent, not the final visual polish pass a production launch would
  get.
- **Admin/observability dashboard.** Every number it would show (token
  usage, cost, iteration counts, tool-call counts) is already tracked on
  `agent_runs` and queryable; there's no UI surfacing it beyond the
  per-trip agent execution view.
- **Dark/light theme toggle.** The app ships dark-only (the design is
  built around it — see `frontend/src/index.css`); a light variant would
  need a second token set, not just an inversion.
- **Full WCAG accessibility audit.** Semantic HTML and focus states are
  used throughout, but this hasn't had a dedicated accessibility pass
  (screen-reader testing, full keyboard-nav audit, contrast verification
  beyond the obvious).
- **Rate limiting** on the API. See `docs/security.md`.

## Genuine open questions, not just missing features

- **Fine-grained (not per-branch) partial replanning.** The current
  replanning strategy reenters at the earliest affected node *per
  parallel branch* (see `docs/agent-architecture.md`) — correct and
  bug-tested, but coarser than a true per-node dependency graph would be.
  E.g. a change that only affects `weather_season` still flows through
  the rest of the shared tail (`budget_optimizer`, `itinerary_generator`)
  even though nothing upstream of it in that tail actually needs to
  rerun. Implementing genuinely fine-grained reruns would mean moving from
  static graph edges to LangGraph's `Send` API for dynamic per-node
  dispatch with correct join semantics — meaningfully more complex to get
  right, and the coarser version already demonstrates the core
  "genuinely agentic, not fake" requirement (it does skip *unaffected
  branches* entirely, which is the expensive part).
- **Real per-run cost/tool-call/time enforcement.** `MAX_LLM_COST_USD`,
  `MAX_TOOL_CALLS`, and `MAX_TRIP_PLANNING_TIME_SECONDS` are read into
  settings and tracked, but only `MAX_AGENT_ITERATIONS` actually gates
  execution today.
