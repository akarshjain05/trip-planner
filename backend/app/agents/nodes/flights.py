from __future__ import annotations
import datetime as dt
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update, with_provider_fallback
from app.agents.state import TripState
from app.schemas.domain import FlightOptionModel, TripRequirements
from app.tools.cache import cached, make_cache_key
from app.tools.flights.mock import MockFlightProvider


def make_flight_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "flight_research", "Searching flight options...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        origin = req.origin or "Unspecified"
        
        # Use IATA codes if the LLM provided them, else fallback to city names
        search_dest = req.destination_iata or destination
        search_orig = req.origin_iata or origin
        
        start = dt.date.fromisoformat(req.start_date) if isinstance(req.start_date, str) else req.start_date
        end = dt.date.fromisoformat(req.end_date) if isinstance(req.end_date, str) else req.end_date

        key = make_cache_key("flights", origin=search_orig, destination=search_dest, depart=str(start), ret=str(end))

        async def fetch():
            if origin == "Unspecified" or destination == "Unspecified":
                return []
            
            # 1. Search outbound flights (one-way)
            outbound = await with_provider_fallback(
                deps, state, "flight_research",
                deps.flight_provider.search_flights(search_orig, search_dest, start, None, max(req.adults, 1)),
                MockFlightProvider().search_flights(search_orig, search_dest, start, None, max(req.adults, 1)),
            )
            
            # 2. Search return flights (one-way, origin and destination reversed)
            inbound = []
            if end:
                inbound = await with_provider_fallback(
                    deps, state, "flight_research",
                    deps.flight_provider.search_flights(search_dest, search_orig, end, None, max(req.adults, 1)),
                    MockFlightProvider().search_flights(search_dest, search_orig, end, None, max(req.adults, 1)),
                )
            
            # Take top 6 cheapest from each leg to ensure the LLM sees both directions
            outbound_top = sorted(outbound, key=lambda f: f.price or 999999)[:6]
            inbound_top = sorted(inbound, key=lambda f: f.price or 999999)[:6]
            
            combined = outbound_top + inbound_top
            return [o.model_dump(mode="json") for o in combined]

        raw, hit = await cached(key, deps.settings.CACHE_TTL_FLIGHTS, fetch)
        options = [FlightOptionModel(**d) for d in raw]
        
        target = req.budget_currency or "INR"
        for f in options:
            if f.currency and f.currency.upper() != target.upper():
                try:
                    rate = await deps.currency_provider.get_rate(f.currency.upper(), target.upper())
                    f.price = round(f.price * rate, 2)
                    f.currency = target.upper()
                except Exception as e:
                    from app.core.logging import get_logger
                    get_logger(__name__).warning("currency_conversion_failed", provider=f.provider, error=str(e))

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
