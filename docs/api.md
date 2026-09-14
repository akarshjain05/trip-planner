# API reference

Full interactive docs (generated from the actual FastAPI app, always
in sync with the code) are at `GET /docs` when the backend is running.
This is a summary; see `/docs` for exact request/response schemas.

All routes except `/auth/register` and `/auth/login` require
`Authorization: Bearer <access_token>`.

## Auth

| Method | Path | |
|---|---|---|
| POST | `/api/auth/register` | Create an account, returns a token pair |
| POST | `/api/auth/login` | Returns a token pair |
| POST | `/api/auth/refresh` | Exchange a refresh token for a new pair |
| GET | `/api/auth/me` | Current user |
| GET | `/api/oauth/google/login` | Redirects to Google for OAuth login |
| GET | `/api/oauth/google/auth` | Google OAuth callback handler, issues tokens |

## Users

| Method | Path | |
|---|---|---|
| GET | `/api/users/me/preferences` | |
| PUT | `/api/users/me/preferences` | Partial update |

## Trips

| Method | Path | |
|---|---|---|
| POST | `/api/trips` | Create a draft trip from a prompt |
| GET | `/api/trips` | List your trips |
| GET | `/api/trips/{id}` | |
| DELETE | `/api/trips/{id}` | |
| POST | `/api/trips/{id}/plan` | Start planning, or (if `awaiting_input`) resume with `{"message": "..."}`. Returns `202`; runs in the background. |
| POST | `/api/trips/{id}/modify` | `{"message": "Hotels are too expensive."}` — triggers a targeted partial replan. Returns `202`. |
| POST | `/api/trips/{id}/regenerate` | Full re-plan from destination research onward. Returns `202`. |
| POST | `/api/trips/{id}/feedback` | Record a note without triggering replanning |
| GET | `/api/trips/{id}/status` | Current status, `awaiting_input`, `clarifying_question` |
| GET | `/api/trips/{id}/itinerary` | Latest itinerary version, with days/activities |
| GET | `/api/trips/{id}/budget` | Latest budget breakdown |
| GET | `/api/trips/{id}/sources` | Web-research sources with provenance |
| GET | `/api/trips/{id}/stream` | SSE live progress (see below) |
| PUT | `/api/trips/{id}/itinerary/days/{day_id}/activities/reorder` | Update the `order_index` of activities within a day (drag-and-drop) |

## Agent runs

| Method | Path | |
|---|---|---|
| GET | `/api/agent-runs/{id}` | Full event history for one planning run |

## Admin

| Method | Path | |
|---|---|---|
| GET | `/api/admin/stats` | Aggregated token usage, cost, and iteration counts across all users. Requires `is_admin=true`. |

## SSE stream

`GET /api/trips/{id}/stream?token=<access_token>`

The browser's native `EventSource` can't set an `Authorization` header, so
this route accepts the token as a query parameter — a standard,
well-established pattern for SSE auth (the header path still works for
any client that can set one; see `_resolve_user_for_stream` in
`app/api/routes/planning.py`).

Each frame is `event: <type>` / `data: <json>`. Types: `agent_started`,
`agent_completed`, `tool_started`, `tool_completed`, `search_result`,
`budget_updated`, `critic_result`, `replanning`, `completed`, `error`.
See `docs/sample-sse-trace.md` for a real captured sequence.

## Typical flow

```
POST /trips              -> {id, status: "draft"}
POST /trips/{id}/plan    -> 202  (open the SSE stream around here)
  ... poll /status or watch the stream ...
  status becomes "awaiting_input" (missing a required field)
    -> POST /trips/{id}/plan {"message": "Mumbai"}   # answers it
  status becomes "completed"
GET /trips/{id}/itinerary
GET /trips/{id}/budget
POST /trips/{id}/modify {"message": "Remove museums."}   -> 202
  ... status becomes "planning" again, then "completed" ...
GET /trips/{id}/itinerary   # new version, only the affected agents reran
```
