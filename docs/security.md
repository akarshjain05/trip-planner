# Security

## Auth

- Passwords hashed with bcrypt (via passlib).
- JWT access tokens (30 min default) + refresh tokens (14 days default),
  `HS256`, signed with `SECRET_KEY` — **change this for anything beyond
  local dev**; a hardcoded example key ships in `.env.example` and must
  never be reused.
- Every trip-scoped route filters by `Trip.user_id == current_user.id` at
  the query level (not just an app-level check after fetching) — a
  request for someone else's trip 404s rather than 403ing, so trip
  existence isn't leaked either. Covered by
  `test_cannot_plan_someone_elses_trip` and the SSE-equivalent tests in
  `test_sse_stream.py`.

## Input validation

Every request body is a Pydantic v2 model — FastAPI rejects malformed
input before it reaches route logic. SQL is never string-built; all
queries go through SQLAlchemy's ORM/Core query builder.

## CORS

Configured via `CORS_ORIGINS` (`.env`), not wildcarded. Add your deployed
frontend origin explicitly rather than using `*` in anything but local
dev.

## Secrets

- `.env` is gitignored; only `.env.example` (with placeholder/empty
  values) is committed.
- No API key is ever sent to the frontend — every external call (LLM,
  travel providers) happens server-side; the browser only ever talks to
  this backend.

## SSRF surface

The only place this app fetches arbitrary URLs is the web-search tool
(`app/tools/web_search/`). The mock provider never makes a network call.
The real Tavily adapter calls a single fixed, hardcoded API host — it
does not fetch or follow URLs supplied by user input, which is the
specific pattern that creates SSRF risk in "let an agent browse the web"
designs.

## Rate limiting

Not implemented in this build. `MAX_AGENT_ITERATIONS` bounds a single
planning run's cost, but there's no per-user or per-IP request-rate
limiter on the API itself yet — see `docs/future-improvements.md`. For a
real deployment, put this at the reverse-proxy layer (e.g. nginx
`limit_req`) or add `slowapi`/similar before exposing this publicly.

## Known gaps (see `docs/future-improvements.md` for the full list)

- **Authentication:** Email/password via JWT. (A Google OAuth backend route exists as a stub, but is not fully supported).
- No account lockout after repeated failed logins.
- No audit log of admin-level actions (there's no admin role yet).
