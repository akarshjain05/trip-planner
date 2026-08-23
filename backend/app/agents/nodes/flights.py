from __future__ import annotations
import datetime as dt
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update
from app.agents.state import TripState
from app.schemas.domain import FlightOptionModel, TripRequirements
from app.tools.cache import cached, make_cache_key


def make_flight_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "flight_research", "Searching flight options...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        origin = req.origin or "Unspecified"
        start = dt.date.fromisoformat(req.start_date) if isinstance(req.start_date, str) else req.start_date

        key = make_cache_key("flights", origin=origin, destination=destination, depart=str(start))

        async def fetch():
            options = await deps.flight_provider.search_flights(origin, destination, start, None, max(req.adults, 1))
            return [o.model_dump(mode="json") for o in options]

        raw, hit = await cached(key, deps.settings.CACHE_TTL_FLIGHTS, fetch)
        options = [FlightOptionModel(**d) for d in raw]
        prioritize_cost = state.get("iteration_count", 0) > 0
        result = await deps.orchestrator.rank_flights(req, options, prioritize_cost=prioritize_cost)
        selected: list[FlightOptionModel] = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_completed", "flight_research",
                         f"Found {len(options)} flights, selected {len(selected)}.", {"cache_hit": hit})
        return {
            "flights": [f.model_dump(mode="json") for f in selected],
            "tool_call_count": bump_tool_calls(state),
            **usage_update(state, result.usage),
        }
    return node
