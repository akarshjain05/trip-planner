from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import bump_tool_calls, usage_update
from app.agents.state import TripState
from app.schemas.domain import PlaceModel, TripRequirements
from app.tools.cache import cached, make_cache_key


def make_places_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "places_research", "Finding attractions and experiences...")
        req = TripRequirements(**state["requirements"])
        destination = state.get("destination") or req.destination or "Unspecified"
        key = make_cache_key("places", destination=destination)

        async def fetch():
            options = await deps.places_provider.search_places(destination, req.activity_preferences)
            return [o.model_dump(mode="json") for o in options]

        raw, hit = await cached(key, deps.settings.CACHE_TTL_PLACES, fetch)
        options = [PlaceModel(**d) for d in raw]
        relax = state.get("iteration_count", 0) > 0
        result = await deps.orchestrator.rank_places(req, options, relax_crowd_filter=relax)
        selected: list[PlaceModel] = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_completed", "places_research",
                         f"Found {len(options)} places, ranked {len(selected)}.", {"cache_hit": hit})
        return {
            "places": [p.model_dump(mode="json") for p in selected],
            "tool_call_count": bump_tool_calls(state),
            **usage_update(state, result.usage),
        }
    return node
