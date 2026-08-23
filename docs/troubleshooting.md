# Troubleshooting

**Backend won't start: `connection refused` to Postgres/Redis.**
Not running, or `.env` points somewhere else. Docker Compose: check
`docker compose ps` and `docker compose logs postgres redis`. Local:
confirm the services are actually up (`pg_isready`, `redis-cli ping`) and
that `DATABASE_URL`/`REDIS_URL` in `backend/.env` match where they're
listening.

**`alembic upgrade head` fails with "relation already exists."**
The database already has tables from a previous run that Alembic doesn't
know about (e.g. created via `Base.metadata.create_all()` during manual
testing rather than migrations). Drop and recreate the database, or
`alembic stamp head` if you're confident the schema already matches.

**Trip gets stuck in `planning` forever.**
Check the backend logs for an exception in the background task — errors
there mark the run `failed` and the trip `failed`, but if the process
itself crashed mid-run (not just the task raising), the trip can be left
in `planning` with no running task behind it. `POST /trips/{id}/regenerate`
starts a fresh run and will move it out of the stuck state.

**SSE stream connects but no events ever arrive.**
Confirm planning was actually triggered (`POST /trips/{id}/plan` or
`/modify`) — the stream only relays events published by an active run; it
has no historical replay. If you missed the live window, the full event
history for the run is still available via
`GET /agent-runs/{id}`.

**`401` on `/trips/{id}/stream` despite being logged in.**
The browser's `EventSource` can't set an `Authorization` header — the
token has to be a query parameter: `?token=<access_token>`. This is
handled automatically by the frontend's `streamUrl()` helper
(`frontend/src/services/api.ts`); if you're calling the stream directly,
make sure you're passing the token the same way.

**Itinerary always ends up "over budget, unresolved" for the exact
example prompt from the spec.** This isn't necessarily a bug — with the
shipped mock pricing, ₹1,50,000 for 2 travelers / 8 days to Japan
*including flights* is genuinely tight. Try a larger budget (e.g.
₹3,50,000) to see the clean single-pass approval path, or connect a real
LLM/providers for more realistic numbers. See
`docs/agent-architecture.md`'s worked example.

**`ModuleNotFoundError` / import errors running `pytest` directly.**
Run it as `python -m pytest` from `backend/`, not `pytest` from
elsewhere — the former puts `backend/` on `sys.path` the way the app
expects; run from the wrong directory and `app.*` imports won't resolve.

**Frontend shows a blank page / network errors in the console.**
Check `VITE_API_BASE_URL` in `frontend/.env` matches the backend's actual
host and port, and that CORS_ORIGINS on the backend includes the
frontend's origin.
