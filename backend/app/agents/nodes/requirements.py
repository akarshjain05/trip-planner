"""Trip Requirement Agent + Missing Info Checker (spec section 4 / graph
diagram nodes 1-2). The output of requirement_extractor -- a validated
TripRequirements -- is exactly the input every downstream node consumes."""
from __future__ import annotations

from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import MissingInfoResult, TripRequirements


def make_requirement_extractor_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "requirement_extractor", "Understanding your trip request...")
        base = TripRequirements(**state["requirements"]) if state.get("requirements") else None
        prior_missing = (state.get("missing_info") or {}).get("missing_fields")
        result = await deps.orchestrator.extract_requirements(state["user_message"], base, prior_missing)
        req: TripRequirements = result.value
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed",
                         "requirement_extractor", "Extracted your trip requirements.",
                         {"requirements": req.model_dump(mode="json")})
        return {
            "requirements": req.model_dump(mode="json"),
            **usage_update(state, result.usage),
        }
    return node


def make_missing_info_checker_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "missing_info_checker", "Checking whether anything critical is missing...")
        req = TripRequirements(**state["requirements"])
        result = await deps.orchestrator.check_missing_info(req)
        mi: MissingInfoResult = result.value
        awaiting = not mi.can_proceed
        await deps.emit(
            state["trip_id"], state["agent_run_id"], "agent_completed", "missing_info_checker",
            mi.clarifying_question if awaiting else "All required trip details are present.",
            {"missing_fields": mi.missing_fields, "awaiting_input": awaiting},
        )
        return {
            "missing_info": mi.model_dump(),
            "awaiting_input": awaiting,
            **usage_update(state, result.usage),
        }
    return node


def route_after_missing_info(state: TripState) -> str:
    from langgraph.graph import END
    return END if state.get("awaiting_input") else "destination_research"
