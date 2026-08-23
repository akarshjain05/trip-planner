from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import HotelOptionModel, TransportationPlan, TripRequirements


def make_transportation_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "transportation", "Optimizing local and airport transportation...")
        req = TripRequirements(**state["requirements"])
        hotels = [HotelOptionModel(**h) for h in state.get("hotels", [])]
        hotel = hotels[0] if hotels else None
        result = await deps.orchestrator.plan_transportation(req, hotel)
        plan: TransportationPlan = result.value
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed",
                         "transportation", "Transportation plan ready.", {})
        return {
            "transportation_plan": plan.model_dump(mode="json"),
            **usage_update(state, result.usage),
        }
    return node
