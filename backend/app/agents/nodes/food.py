from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update, with_provider_fallback
from app.agents.state import TripState
from app.schemas.domain import RestaurantModel, TripRequirements
from app.tools.cache import cached, make_cache_key
from app.tools.restaurants.mock import MockRestaurantProvider


def make_food_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "food_research", "Finding restaurants and food experiences...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        key = make_cache_key("restaurants", destination=destination)

        async def fetch():
            options = await with_provider_fallback(
                deps, state, "food_research",
                deps.restaurant_provider.search_restaurants(destination, req.food_preferences),
                MockRestaurantProvider().search_restaurants(destination, req.food_preferences),
            )
            return [o.model_dump(mode="json") for o in options]

        raw, hit = await cached(key, deps.settings.CACHE_TTL_PLACES, fetch)
        options = [RestaurantModel(**d) for d in raw]
        result = await deps.orchestrator.rank_restaurants(req, options)
        selected: list[RestaurantModel] = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_completed", "food_research",
                         f"Found {len(options)} restaurants, ranked {len(selected)}.", {"cache_hit": hit})
        return {
            "restaurants": [r.model_dump(mode="json") for r in selected],
            "tool_call_count": bump_tool_calls(state),
            **usage_update(state, result.usage),
        }
    return node
