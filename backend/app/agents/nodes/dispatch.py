"""Graph entry dispatcher.

Every invocation of the compiled graph -- a brand-new trip, resuming after
a clarifying question, or a user-driven partial replan -- enters here
first. This is what lets a single compiled graph serve all three cases
without needing to "resume mid-graph" through exotic APIs: a modification
request is resolved to a target node *before* the graph runs (see
app/services/trip_service.py), and this node just routes to it.
"""
from __future__ import annotations

from app.agents.state import TripState


async def dispatch_node(state: TripState) -> dict:
    return {}  # pure router; no state changes


def route_dispatch(state: TripState) -> str | list[str]:
    if state.get("trigger") == "modification" and state.get("replan_target"):
        return state["replan_target"]
    return "requirement_extractor"
