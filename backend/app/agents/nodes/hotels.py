from __future__ import annotations
import datetime as dt
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update, with_provider_fallback
from app.agents.state import TripState
from app.schemas.domain import HotelOptionModel, TripRequirements
from app.tools.cache import cached, make_cache_key
from app.tools.hotels.mock import MockHotelProvider


def make_hotel_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "hotel_research", "Comparing hotels...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        start = dt.date.fromisoformat(req.start_date) if isinstance(req.start_date, str) else req.start_date
        end = dt.date.fromisoformat(req.end_date) if isinstance(req.end_date, str) else req.end_date

        key = make_cache_key("hotels", destination=destination, checkin=str(start))

        async def fetch():
            options = await with_provider_fallback(
                deps, state, "hotel_research",
                deps.hotel_provider.search_hotels(destination, start, end, max(req.adults, 1)),
                MockHotelProvider().search_hotels(destination, start, end, max(req.adults, 1)),
            )
            return [o.model_dump(mode="json") for o in options]

        raw, hit = await cached(key, deps.settings.CACHE_TTL_HOTELS, fetch)
        options = [HotelOptionModel(**d) for d in raw]
        result = await deps.orchestrator.rank_hotels(req, options)
        selected: list[HotelOptionModel] = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_completed", "hotel_research",
                         f"Found {len(options)} hotels, selected {len(selected)}.", {"cache_hit": hit})
        return {
            "hotels": [h.model_dump(mode="json") for h in selected],
            "tool_call_count": bump_tool_calls(state),
            **usage_update(state, result.usage),
        }
    return node
