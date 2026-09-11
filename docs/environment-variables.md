# Environment variables

Full reference for `backend/.env` (see `backend/.env.example` for the
copy-pasteable version with the same comments) and `frontend/.env`.

## Backend

| Variable | Default | Notes |
|---|---|---|
| `APP_NAME` | `AI Trip Planner` | |
| `ENVIRONMENT` | `development` | `development` \| `test` \| `production` |
| `DEBUG` | `true` | Verbose console logging |
| `API_PREFIX` | `/api` | |
| `BACKEND_PORT` | `8000` | |
| `SECRET_KEY` | dev placeholder | **Change for anything beyond local dev.** Signs JWTs. |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | |
| `CORS_ORIGINS` | localhost:5173/5183 | JSON array |
| `DATABASE_URL` | local Postgres | Must be an `asyncpg` URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | local Redis | |
| `DEMO_MODE` | `true` | Forces every provider (including the LLM) onto deterministic mock logic |
| `LLM_PROVIDER` | `mock` | `openai` \| `anthropic` \| `google` \| `openrouter` \| `mock` |
| `LLM_MODEL` | `gpt-4o-mini` | Any model string your provider accepts |
| `LLM_TEMPERATURE` | `0.3` | |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY` / `OPENROUTER_API_KEY` | empty | Only the one matching `LLM_PROVIDER` is used |
| `OPENROUTER_BASE_URL` | OpenRouter's API URL | Only relevant for `LLM_PROVIDER=openrouter` |
| `FLIGHTS_PROVIDER` | `mock` | `mock` \| `amadeus` |
| `HOTELS_PROVIDER` | `mock` | `mock` \| `booking` (interface only — see `docs/providers.md`) |
| `PLACES_PROVIDER` | `mock` | `mock` \| `google_places` |
| `WEATHER_PROVIDER` | `mock` | `mock` \| `open_meteo` (no key needed) |
| `CURRENCY_PROVIDER` | `mock` | `mock` \| `exchange_rate_api` |
| `WEB_SEARCH_PROVIDER` | `mock` | `mock` \| `tavily` |
| `AMADEUS_API_KEY` / `AMADEUS_API_SECRET` | empty | Amadeus test-environment credentials |
| `GOOGLE_PLACES_API_KEY` | empty | Also reused by the Google Directions adapter interface |
| `OPENWEATHER_API_KEY` | empty | Reserved; Open-Meteo (the wired real adapter) needs no key |
| `TAVILY_API_KEY` | empty | |
| `MAX_AGENT_ITERATIONS` | `3` | Hard cap on critic → replan loops per run |
| `MAX_TOOL_CALLS` | `40` | Reserved for future per-run tool-call limiting |
| `MAX_LLM_COST_USD` | `2.00` | Reserved for future per-run cost limiting |
| `MAX_TRIP_PLANNING_TIME_SECONDS` | `180` | Reserved for future wall-clock limiting |
| `CACHE_TTL_WEATHER` / `_CURRENCY` / `_PLACES` / `_FLIGHTS` / `_HOTELS` / `_LLM` | various | Redis cache TTLs, seconds |

`MAX_TOOL_CALLS`, `MAX_LLM_COST_USD`, and `MAX_TRIP_PLANNING_TIME_SECONDS`
are read into `Settings` and are available to wire into new guard checks,
but only `MAX_AGENT_ITERATIONS` is actively enforced by the graph today
(via `route_after_critic`) — noted honestly rather than implying all four
are live limits.

## Frontend

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Must match your backend's actual host/port |
