from __future__ import annotations
import datetime as dt
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update, with_provider_fallback
from app.agents.state import TripState
from app.schemas.domain import TripRequirements, WeatherOutlook
from app.tools.cache import cached, make_cache_key
from app.tools.weather.mock import MockWeatherProvider


def make_weather_season_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "weather_season", "Checking weather and seasonality...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        start = dt.date.fromisoformat(req.start_date) if isinstance(req.start_date, str) else req.start_date
        days = req.duration_days or 1

        key = make_cache_key("weather", destination=destination, start=str(start), days=days)

        async def fetch():
            return await with_provider_fallback(
                deps, state, "weather_season",
                deps.weather_provider.get_forecast(destination, start, days),
                MockWeatherProvider().get_forecast(destination, start, days),
            )

        raw, hit = await cached(key, deps.settings.CACHE_TTL_WEATHER, fetch)

        result = await deps.orchestrator.weather_outlook(req)
        outlook: WeatherOutlook = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_completed", "weather_season",
                         f"Weather outlook ready for {len(outlook.days)} day(s).", {"cache_hit": hit, "raw_source": raw[0].get("is_mock") if raw else None})
        return {
            "weather": outlook.model_dump(mode="json"),
            "tool_call_count": bump_tool_calls(state),
            **usage_update(state, result.usage),
        }
    return node
