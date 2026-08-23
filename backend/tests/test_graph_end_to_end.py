"""
End-to-end tests of the compiled LangGraph workflow itself (not through
the API/DB layer -- see test_api_trips.py for that). These are the
formalized version of the manual testing done while building the graph.
"""
from __future__ import annotations

import uuid

import pytest

from app.agents.deps import NodeDeps
from app.agents.graph import build_trip_graph
from app.ai.orchestrator import LLMOrchestrator
from app.core.config import get_settings
from app.tools.factory import (
    get_currency_provider,
    get_flight_provider,
    get_hotel_provider,
    get_maps_provider,
    get_places_provider,
    get_restaurant_provider,
    get_weather_provider,
    get_web_search_provider,
)

CANONICAL_PROMPT = (
    "I want to visit Japan for 8 days in October. My budget is Rs 350000. "
    "I like nature, anime, food and photography. I dont like crowded tourist "
    "attractions. I am traveling with one friend. I prefer comfortable hotels "
    "and dont want extremely long travel days. I am flying from Mumbai."
)

TIGHT_BUDGET_PROMPT = CANONICAL_PROMPT.replace("350000", "150000")


def _build_graph_and_deps():
    settings = get_settings()
    events: list[tuple] = []

    async def emit(trip_id, run_id, event_type, agent_name=None, message=None, payload=None):
        events.append((event_type, agent_name, message))

    deps = NodeDeps(
        settings=settings, orchestrator=LLMOrchestrator(settings),
        flight_provider=get_flight_provider(settings), hotel_provider=get_hotel_provider(settings),
        places_provider=get_places_provider(settings), restaurant_provider=get_restaurant_provider(settings),
        weather_provider=get_weather_provider(settings), currency_provider=get_currency_provider(settings),
        maps_provider=get_maps_provider(settings), web_search_provider=get_web_search_provider(settings),
        emit=emit,
    )
    return build_trip_graph(deps), events


def _initial_state(message: str, trip_id: str, **overrides) -> dict:
    state = {
        "trip_id": trip_id, "agent_run_id": str(uuid.uuid4()), "trigger": "initial_plan",
        "user_message": message, "requirements": {}, "max_iterations": 3,
    }
    state.update(overrides)
    return state


class TestMissingInfoInterrupt:
    @pytest.mark.asyncio
    async def test_stops_and_asks_for_missing_origin(self):
        graph, _events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}}
        prompt_without_origin = CANONICAL_PROMPT.replace(" I am flying from Mumbai.", "")
        result = await graph.ainvoke(_initial_state(prompt_without_origin, trip_id), config)
        assert result["awaiting_input"] is True
        assert "origin" in result["missing_info"]["missing_fields"]
        assert result.get("final") is not True

    @pytest.mark.asyncio
    async def test_resumes_correctly_with_bare_reply(self):
        graph, _events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        prompt_without_origin = CANONICAL_PROMPT.replace(" I am flying from Mumbai.", "")
        r1 = await graph.ainvoke(_initial_state(prompt_without_origin, trip_id), config)
        assert r1["awaiting_input"] is True

        r2 = await graph.ainvoke({**r1, "trigger": "initial_plan", "user_message": "Mumbai"}, config)
        assert r2["awaiting_input"] is False
        assert r2["requirements"]["origin"] == "Mumbai"
        assert r2.get("itinerary") is not None


class TestFullPlanningRun:
    @pytest.mark.asyncio
    async def test_satisfiable_budget_converges_to_approval(self):
        graph, _events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        result = await graph.ainvoke(_initial_state(CANONICAL_PROMPT, trip_id), config)

        assert result["final"] is True
        assert result["itinerary"]["days"]
        assert len(result["itinerary"]["days"]) == 8
        for day in result["itinerary"]["days"]:
            assert len(day["activities"]) > 0

    @pytest.mark.asyncio
    async def test_output_of_each_stage_flows_into_the_next(self):
        """The core 'genuinely agentic' claim: destination feeds flights/
        hotels, which feed the itinerary, which feeds the critic."""
        graph, _events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        result = await graph.ainvoke(_initial_state(CANONICAL_PROMPT, trip_id), config)

        assert result["destination"] == "Japan"
        assert all(f["destination"] for f in result["flights"])
        flight_titles = [
            a["title"] for day in result["itinerary"]["days"] for a in day["activities"]
            if a["activity_type"] == "flight"
        ]
        assert any(result["flights"][0]["airline"] in t for t in flight_titles if t)
        assert result["itinerary"]["total_estimated_cost"] == result["budget"]["total_estimated"]

    @pytest.mark.asyncio
    async def test_impossible_budget_exhausts_iterations_and_reports_honestly(self):
        """A budget no optimization could ever satisfy must still terminate
        (not loop forever) and must never claim success."""
        graph, events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        impossible_prompt = CANONICAL_PROMPT.replace("350000", "1000")
        result = await graph.ainvoke(_initial_state(impossible_prompt, trip_id, max_iterations=3), config)

        assert result["final"] is True
        assert result["iteration_count"] == 3
        assert result["critic_result"]["approved"] is False
        assert result["budget"]["over_budget"] is True
        finalize_events = [e for e in events if e[1] == "finalize"]
        assert len(finalize_events) == 1
        assert "iteration limit" in (finalize_events[0][2] or "")

    @pytest.mark.asyncio
    async def test_tight_budget_never_exceeds_cap_or_silently_approves(self):
        graph, _events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        result = await graph.ainvoke(_initial_state(TIGHT_BUDGET_PROMPT, trip_id, max_iterations=3), config)

        assert result["final"] is True
        assert 1 <= result["iteration_count"] <= 3
        # A genuinely unresolved budget issue must never be silently marked approved.
        if result["budget"]["over_budget"]:
            assert result["critic_result"]["approved"] is False


class TestPartialReplanning:
    @pytest.mark.asyncio
    async def test_replanning_does_not_runaway_duplicate(self):
        """The key 'dependency-aware partial replanning' proof: even across
        several replan iterations, no node re-executes an unbounded number
        of times (the asymmetric-depth join bug would show up here as
        agent_started counts roughly doubling every iteration)."""
        graph, events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        result = await graph.ainvoke(_initial_state(TIGHT_BUDGET_PROMPT, trip_id), config)

        hotel_starts = sum(1 for e in events if e[1] == "hotel_research" and e[0] == "agent_started")
        assert hotel_starts <= result["iteration_count"] + 1
        finalize_events = [e for e in events if e[1] == "finalize"]
        assert len(finalize_events) == 1

    @pytest.mark.asyncio
    async def test_max_iterations_is_respected(self):
        graph, events = _build_graph_and_deps()
        trip_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": trip_id}, "recursion_limit": 60}
        result = await graph.ainvoke(_initial_state(TIGHT_BUDGET_PROMPT, trip_id, max_iterations=2), config)
        assert result["iteration_count"] <= 2
        finalize_events = [e for e in events if e[1] == "finalize"]
        assert len(finalize_events) == 1
