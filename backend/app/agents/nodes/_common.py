"""Small helpers shared by every node to avoid repeating the same
usage-aggregation / tool-call-counting boilerplate in each file.

These return *deltas*, not running totals -- the corresponding TripState
fields use an operator.add reducer (see app/agents/state.py) precisely so
that parallel branches (flight_research + hotel_research running in the
same superstep, etc.) can both write in the same step without conflicting.
"""
from __future__ import annotations

from app.ai.orchestrator import UsageInfo


def usage_update(state, usage: UsageInfo) -> dict:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd": round(usage.estimated_cost_usd, 6),
    }


def bump_tool_calls(state, n: int = 1) -> int:
    return n

from app.tools.base import ProviderError

async def with_provider_fallback(deps, state, node_name: str, primary_coro, mock_coro):
    """
    Executes primary_coro. If it raises a ProviderError, emits a warning event
    and falls back to mock_coro.
    """
    try:
        return await primary_coro
    except ProviderError as e:
        await deps.emit(
            state["trip_id"], 
            state["agent_run_id"], 
            "tool_completed", 
            node_name, 
            f"Provider '{e.provider}' failed, falling back to mock data."
        )
        return await mock_coro
