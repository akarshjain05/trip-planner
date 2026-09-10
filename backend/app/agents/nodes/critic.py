"""
The Critic + Replanning loop (spec sections 5 and 3's graph diagram).

critic_node reviews the itinerary and votes approve/reject.
route_after_critic decides: finalize, or send the workflow backward.
replanner_node picks exactly where in the pipeline to resume -- the
earliest node named in the critic's recommended_searches -- so everything
BEFORE that point (already-good research) is not redone.
route_after_replanner performs that backward jump.
finalize_node marks the run done and emits the terminal event.
"""
from __future__ import annotations

from langgraph.graph import END

from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import BudgetBreakdown, CriticResult, ItineraryModel, PlaceModel, TripRequirements


def make_critic_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "critic", "Reviewing the itinerary for problems...")
        req = TripRequirements(**state["requirements"])
        itinerary = ItineraryModel(**state["itinerary"])
        budget = BudgetBreakdown(**state["budget"])
        places = [PlaceModel(**p) for p in state.get("places", [])]

        result = await deps.orchestrator.critic_review(req, itinerary, budget, places)
        critic: CriticResult = result.value

        iteration = state.get("iteration_count", 0) + 1
        revisions = [*state.get("revisions", []), critic.model_dump(mode="json")]

        if critic.approved:
            msg = "Itinerary approved -- no blocking issues found."
        else:
            msg = f"Found {len(critic.issues)} issue(s): " + "; ".join(i.description for i in critic.issues[:3])

        await deps.emit(state["trip_id"], state["agent_run_id"], "critic_result", "critic", msg, {
            "approved": critic.approved, "severity": critic.severity,
            "issue_count": len(critic.issues), "iteration": iteration,
            "recommended_searches": critic.recommended_searches,
        })
        return {
            "critic_result": critic.model_dump(mode="json"),
            "iteration_count": iteration,
            "revisions": revisions,
            **usage_update(state, result.usage),
        }
    return node


def route_after_critic(state: TripState) -> str:
    critic = state.get("critic_result") or {}
    iteration = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    if critic.get("approved") or iteration >= max_iterations:
        return "finalize"
    return "replanner"


def make_replanner_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        critic = state.get("critic_result") or {}
        targets = critic.get("recommended_searches", [])

        await deps.emit(
            state["trip_id"], state["agent_run_id"], "replanning", "replanner",
            f"Re-running from {targets} to address the critic's findings.",
            {"recommended_searches": critic.get("recommended_searches", []), "resuming_from": targets,
             "iteration": state.get("iteration_count", 0)},
        )
        return {"replan_target": targets}
    return node


def route_after_replanner(state: TripState) -> list[str]:
    return state.get("replan_target") or ["itinerary_generator"]


def make_finalize_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        critic = state.get("critic_result") or {}
        if critic.get("approved"):
            note = "Itinerary approved by the critic."
        else:
            note = (
                f"Reached the {state.get('iteration_count', 0)}-iteration limit with unresolved "
                f"issues (severity: {critic.get('severity', 'unknown')}); delivering the best "
                f"itinerary produced so far rather than looping indefinitely."
            )
        await deps.emit(state["trip_id"], state["agent_run_id"], "completed", "finalize", note, {})
        return {"final": True}
    return node
