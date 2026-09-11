# Tool abstraction

Every external capability an agent can call — flight search, hotel
search, places, restaurants, weather, currency conversion, maps/travel
time, web search — follows the same three-piece pattern under
`backend/app/tools/<category>/`:

```
tools/<category>/
    base.py    # a typing.Protocol defining the interface
    mock.py    # deterministic mock implementation (always available)
    <real>.py  # real adapter(s), where a stable API exists
```

```python
class FlightProvider(Protocol):
    async def search_flights(
        self, origin: str, destination: str,
        depart_date: date | None = None, return_date: date | None = None,
        adults: int = 1, cabin: str = "economy",
    ) -> list[FlightOptionModel]: ...
```

Agent nodes depend on the `Protocol`, never a concrete class.
`app/tools/factory.py` is the single place that reads `.env`
(`FLIGHTS_PROVIDER`, etc.) and `DEMO_MODE` to decide which concrete
implementation to construct. Swapping a provider is a one-line config
change, not a code change — see `docs/providers.md` for exactly which
providers have real adapters and which are interfaces only, and why.

## Cross-cutting: caching, errors, retries

- **Caching** (`app/tools/cache.py`): every provider call and LLM query goes
  through `cached(key, ttl, fetch)`, a thin Redis wrapper keyed by a
  stable hash of its arguments. This allows identical searches (and identical
  prompts during development) within the TTL window to instantly resolve without
  re-hitting external APIs. Tested for real against a local Redis instance
  (`backend/tests/test_tools.py::TestCache`).
- **Normalized errors** (`app/tools/base.py`): every adapter raises
  `ProviderError(provider, message, retriable)` instead of leaking
  SDK-specific exceptions — a node (or future retry wrapper) only ever
  needs to catch one exception type, and `retriable` tells it whether
  retrying makes sense (e.g. a 5xx vs. a missing API key).
- **Timeouts**: every real adapter's HTTP calls (`httpx.AsyncClient(...)`)
  set an explicit timeout rather than relying on a default.

## Why the mock isn't just "return an empty list"

A mock that returns nothing would make the graph structurally runnable
but not actually demonstrate anything — an itinerary with no flights or
attractions doesn't prove the pipeline works. Every mock instead returns
plausible, varied, deterministic data (see `docs/providers.md` for what
"deterministic" buys here), clearly flagged `is_mock: true` at the row
level in Postgres so it's traceable even outside the UI.
