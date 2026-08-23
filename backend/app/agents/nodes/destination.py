from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import DestinationResearchResult, TripRequirements


def make_destination_research_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "destination_research", "Researching destinations that fit your preferences...")
        req = TripRequirements(**state["requirements"])
        result = await deps.orchestrator.research_destinations(req)
        dr: DestinationResearchResult = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "tool_started", "destination_research",
                         f"Searching the web for travel context on {dr.chosen}...")
        web_results = await deps.web_search_provider.search(f"best time to visit {dr.chosen} travel tips")
        await deps.emit(state["trip_id"], state["agent_run_id"], "search_result", "destination_research",
                         f"Found {len(web_results)} supporting source(s).", {"count": len(web_results)})

        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed",
                         "destination_research", f"Chosen destination: {dr.chosen}",
                         {"candidates": [c.model_dump() for c in dr.candidates]})
        return {
            "destination_result": dr.model_dump(mode="json"),
            "destination": dr.chosen,
            "research_sources": web_results,
            **usage_update(state, result.usage),
        }
    return node
