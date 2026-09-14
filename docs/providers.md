# Providers: mock vs. real

Every external dependency — the LLM and every travel-data source — sits
behind a small `Protocol` interface (`app/tools/<category>/base.py`) with
a mock implementation and a real-adapter implementation. `app/tools/factory.py` picks which one to construct from
`.env`; nothing else in the codebase imports a provider class directly.

## What's tested vs. what's an interface

| Category | Mock | Real adapter | Real adapter tested here? |
|---|---|---|---|
| LLM reasoning | ✅ rule-based, deterministic | ✅ NVIDIA/OpenRouter/Groq/Google/OpenAI via LangChain and AsyncOpenAI | ❌ no network egress to these APIs from this build environment |
| Flights | ✅ | ✅ Amadeus, SerpApi, SkyScrapper, Tavily | ❌ |
| Hotels | ✅ | ✅ SerpApi, RapidAPI Booking, Tavily | ❌ |
| Places | ✅ curated + generated fallback | ✅ Google Places (New) | ❌ |
| Restaurants | ✅ | ✅ Tavily | ❌ |
| Weather | ✅ | ✅ Open-Meteo (**no key needed**) | ❌ (no egress), but this is the easiest one to actually turn on yourself |
| Currency | ✅ fixed table | ✅ Frankfurter.app (no key needed) | ❌ |
| Web search | ✅ labeled demo results | ✅ Tavily | ❌ |

## The LLM Failover Pool

Unlike traditional single-provider setups, this backend implements a robust **Multi-Provider Failover Pool** (`app/ai/provider_pool.py`). 

Because free or cheap LLM APIs (like NVIDIA NIMs, Groq, or OpenRouter free tiers) frequently experience cold starts, rate limits, or 504 Gateway Timeouts, the backend handles this gracefully:
- **Daily Caps:** Tracks requests per provider in Redis and automatically fails over when a cap is hit (e.g., `LLM_DAILY_CAP_GROQ=14000`).
- **Streaming Anti-Timeout:** Bypasses LangChain for heavy providers like NVIDIA, using raw `AsyncOpenAI(stream=True)` to stream reasoning tokens over the wire, keeping the HTTP connection alive during 3+ minute "thinking" phases and preventing 504 Gateway Timeouts.
- **Cheap vs. Heavy Routing:** Uses lighter models (`LLM_MODEL_CHEAP_*`) for data extraction tasks and heavier models (`LLM_MODEL_*`) for itinerary generation and critic review.

## Why the mocks look the way they do

- **Deterministic, not random per call.** The same query always returns
  the same options (seeded by a hash of the arguments) — this makes
  caching meaningful and test assertions reproducible.
- **Clearly labeled.** Every mock result carries `is_mock: true` at the
  row level in Postgres, not just in a UI badge.
- **Responsive to retries.** On a critic-triggered retry, `rank_places`
  relaxes its crowd-level filter instead of returning the identical
  result, and `rank_flights` switches to pure cost-sorting instead of the
  comfort-weighted default — otherwise a deterministic mock would make the
  replanning loop pointless (it would just repeat the same rejected
  result forever).

## Turning on a real provider

1. Set the category's `*_PROVIDER` env var (e.g. `WEATHER_PROVIDER=open_meteo`).
2. Set `DEMO_MODE=false` (provider selection is ignored while demo mode
   forces mocks everywhere).
3. Supply the matching API key if the adapter needs one.

Weather (Open-Meteo) and currency (Frankfurter.app) need no key at all,
so they're the fastest to verify end-to-end yourself.
