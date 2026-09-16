# Environment variables

Full reference for `backend/.env` (see `backend/.env.example` for the
copy-pasteable version with the same comments) and `frontend/.env`.

## Backend

| Variable | Default | Notes |
|---|---|---|
| `APP_NAME` | `Itinero` | |
| `ENVIRONMENT` | `development` | `development` \| `test` \| `production` |
| `DEBUG` | `true` | Verbose console logging |
| `API_PREFIX` | `/api` | |
| `BACKEND_PORT` | `8000` | |
| `SECRET_KEY` | dev placeholder | **Change for anything beyond local dev.** Signs JWTs. |
| `SESSION_SECRET_KEY` | dev placeholder | **Change for anything beyond local dev.** Signs OAuth session cookies. |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | |
| `CORS_ORIGINS` | localhost:5173/5183 | JSON array |
| `DATABASE_URL` | local Postgres | Must be an `asyncpg` URL (`postgresql+asyncpg://...`) |
| `REDIS_URL` | local Redis | |
| `DEMO_MODE` | `true` | Forces every provider (including the LLM) onto deterministic mock logic |
| `BACKGROUND_EXECUTOR` | `celery` | `celery` \| `asyncio` |

### LLM Providers (Failover Pool)

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER_CHAIN` | `["mock"]` | JSON array of providers, e.g., `["nvidia", "openrouter", "groq", "google"]` |
| `LLM_MODEL_NVIDIA`, `_OPENROUTER`, `_GROQ`, `_GOOGLE` | various | Heavy/reasoning models for the Critic/Itinerary nodes |
| `LLM_MODEL_CHEAP_NVIDIA`, `_OPENROUTER`, `_GROQ`, `_GOOGLE` | various | Faster/cheaper models for extraction/research tasks |
| `LLM_DAILY_CAP_NVIDIA`, `_OPENROUTER`, `_GROQ`, `_GOOGLE` | `0` | Daily request limits per provider before hard-failing over to the next |
| `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY`, `GOOGLE_API_KEY` | empty | API keys for the configured pool providers |

### Travel & Data Providers

| Variable | Default | Notes |
|---|---|---|
| `FLIGHTS_PROVIDER` | `mock` | `mock` \| `amadeus` |
| `HOTELS_PROVIDER` | `mock` | `mock` \| `serpapi_hotels` \| `rapidapi_booking` \| `tavily_hotels` |
| `PLACES_PROVIDER` | `mock` | `mock` \| `google_places` |
| `FOOD_PROVIDER` | `mock` | `mock` \| `tavily_food` |
| `WEATHER_PROVIDER` | `mock` | `mock` \| `open_meteo` (no key needed) |
| `CURRENCY_PROVIDER` | `mock` | `mock` \| `exchange_rate_api` |
| `WEB_SEARCH_PROVIDER` | `mock` | `mock` \| `tavily` |

**Data Provider API Keys:**
- `AMADEUS_API_KEY` / `AMADEUS_API_SECRET`
- `GOOGLE_PLACES_API_KEY`
- `SERPAPI_KEY`
- `RAPIDAPI_KEY`
- `GEOAPIFY_API_KEY`
- `TAVILY_API_KEY`

### Agent & Cache Controls

| Variable | Default | Notes |
|---|---|---|
| `MAX_AGENT_ITERATIONS` | `3` | Hard cap on critic → replan loops per run |
| `MAX_TOOL_CALLS` | `40` | Reserved for future per-run tool-call limiting |
| `MAX_LLM_COST_USD` | `2.00` | Reserved for future per-run cost limiting |
| `MAX_TRIP_PLANNING_TIME_SECONDS` | `180` | Reserved for future wall-clock limiting |
| `CACHE_TTL_WEATHER`, `_CURRENCY`, `_PLACES`, `_FLIGHTS`, `_HOTELS`, `_LLM` | various | Redis cache TTLs, seconds |

## Frontend

| Variable | Default | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | Must match your backend's actual host/port |

