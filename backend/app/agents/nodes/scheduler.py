from __future__ import annotations
import time
from langgraph.types import Send
from app.agents.state import TripState, DEPENDENCIES, get_transitive_dependents
from app.core.config import get_settings

def scheduler_node(state: TripState) -> dict:
    settings = get_settings()
    now = time.time()
    
    start_time = state.get("start_time")
    if start_time:
        elapsed = now - start_time
        if elapsed > settings.MAX_TRIP_PLANNING_TIME_SECONDS:
            return {"error": f"Planning timed out after {elapsed:.1f}s", "final": True}
    
    if state.get("estimated_cost_usd", 0) > settings.MAX_LLM_COST_USD:
        return {"error": f"Cost limit exceeded: ${state['estimated_cost_usd']:.2f}", "final": True}
        
    if state.get("tool_call_count", 0) > settings.MAX_TOOL_CALLS:
        return {"error": f"Tool call limit exceeded: {state['tool_call_count']}", "final": True}

    updates = {}
    completed = set(state.get("completed_nodes", []))

    replan_targets = state.get("replan_target", [])
    if replan_targets:
        dependents = get_transitive_dependents(replan_targets)
        to_remove = set(replan_targets) | dependents
        to_remove.update({"critic", "replanner", "finalize"})
        new_completed = [n for n in completed if n not in to_remove]
        updates["completed_nodes"] = ["__RESET__"] + new_completed
        updates["replan_target"] = []
        
    return updates

def route_scheduler(state: TripState) -> list[Send] | str:
    completed = set(state.get("completed_nodes", []))
    
    if "finalize" in completed:
        return "__end__"
        
    if state.get("error"):
        return [Send("finalize", state)]
        
    if state.get("awaiting_input"):
        return "__end__"

    pending_to_run = []

    if "critic" in completed and "replanner" not in completed:
        critic_result = state.get("critic_result") or {}
        iteration = state.get("iteration_count", 0)
        max_iterations = state.get("max_iterations", 3)
        
        if state.get("final") or critic_result.get("approved") or iteration >= max_iterations:
            return [Send("finalize", state)]
        else:
            return [Send("replanner", state)]

    for node, deps in DEPENDENCIES.items():
        if node in completed:
            continue
        if node in ["replanner", "finalize"]:
            continue
            
        if all(d in completed for d in deps):
            pending_to_run.append(node)
            
    if pending_to_run:
        return [Send(n, state) for n in pending_to_run]
        
    return "__end__"
