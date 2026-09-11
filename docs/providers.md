# Providers: mock vs. real

Every external dependency — the LLM and every travel-data source — sits
behind a small `Protocol` interface (`app/tools/<category>/base.py`) with
a mock implementation and, for most categories, a real-adapter
implementation. `app/tools/factory.py` picks which one to construct from
`.env`; nothing else in the codebase imports a provider class directly.

## What's tested vs. what's an interface

| Category | Mock | Real adapter | Real adapter tested here? |
|---|---|---|---|
| LLM reasoning | ✅ rule-based, deterministic | ✅ OpenAI/Anthropic/Google/Groq/OpenRouter via LangChain | ❌ no network egress to these APIs from this build environment |
| Flights | ✅ | ✅ Amadeus (test environment) | ❌ |
| Hotels | ✅ | interface only (`booking_stub.py`) | — most hotel APIs need a signed partner agreement, not just a key |
| Places | ✅ curated + generated fallback | ✅ Google Places (New) | ❌ |
| Restaurants | ✅ | interface only (`real_stub.py`) | — |
| Weather | ✅ | ✅ Open-Meteo (**no key needed**) | ❌ (no egress), but this is the easiest one to actually turn on yourself |
| Currency | ✅ fixed table | ✅ Frankfurter.app (no key needed) | ❌ |
| Web search | ✅ labeled demo results | ✅ Tavily | ❌ |

"Interface only" means: a real adapter class exists with the right method
signature and raises a clear `ProviderError` explaining what's missing,
rather than either lying about working or leaving a broken import. This
was a deliberate choice over half-implementing something unverifiable —
see the spec's own instruction: *"If something cannot be fully
implemented because a third-party API requires credentials, implement a
clean provider interface and working mock provider rather than leaving
broken code."*

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
  result forever). This was a real bug caught during testing; see
  `docs/agent-architecture.md`.

## Turning on a real provider

1. Set the category's `*_PROVIDER` env var (e.g. `WEATHER_PROVIDER=open_meteo`).
2. Set `DEMO_MODE=false` (provider selection is ignored while demo mode
   forces mocks everywhere).
3. Supply the matching API key if the adapter needs one.

Weather (Open-Meteo) and currency (Frankfurter.app) need no key at all,
so they're the fastest to verify end-to-end yourself.

## Extending with a new real provider

Follow the shape in `app/tools/flights/amadeus.py` (the most complete
example): implement the category's `Protocol`, normalize the provider's
response into the shared Pydantic model (`FlightOptionModel`, etc.),
raise `ProviderError` on failure with `retriable` set appropriately, and
register it in `app/tools/factory.py`.
