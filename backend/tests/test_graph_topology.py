"""
Tests for the replanning target computation (app/agents/state.py).

These formalize two real, non-obvious LangGraph behaviors discovered
during manual testing:
  1. A join node fires as soon as ANY one predecessor completes -- so
     targeting only one parallel branch is safe and doesn't deadlock.
  2. If two branches are targeted in the SAME replan but at different
     depths, the shallower one reaches the join first, the join fires on
     stale data, then fires AGAIN when the other branch finishes --
     double-executing everything downstream. compute_replan_targets must
     normalize simultaneous multi-branch targets to their branch roots.
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph

from app.agents.state import PARALLEL_BRANCHES, SEQUENTIAL_TAIL, compute_replan_targets


class TestComputeReplanTargets:
    def test_single_branch_hit_returns_specific_node(self):
        assert compute_replan_targets(["hotel_research"]) == ["hotel_research"]
        assert compute_replan_targets(["places_research"]) == ["places_research"]

    def test_two_branches_hit_normalizes_to_branch_roots(self):
        targets = compute_replan_targets(["places_research", "hotel_research"])
        assert set(targets) == {"flight_research", "hotel_research"}

    def test_two_branches_hit_even_when_already_at_roots(self):
        targets = compute_replan_targets(["flight_research", "hotel_research"])
        assert set(targets) == {"flight_research", "hotel_research"}

    def test_tail_only_hit(self):
        assert compute_replan_targets(["budget_optimizer"]) == ["budget_optimizer"]

    def test_branch_and_tail_hit_prefers_branch(self):
        # A branch target's downstream path already covers the tail, so the
        # tail node doesn't need a separate explicit target.
        targets = compute_replan_targets(["hotel_research", "weather_season"])
        assert targets == ["hotel_research"]

    def test_unrecognized_falls_back_to_itinerary_generator(self):
        assert compute_replan_targets([]) == ["itinerary_generator"]
        assert compute_replan_targets(["not_a_real_node"]) == ["itinerary_generator"]

    def test_every_node_is_covered_by_exactly_one_branch_or_tail(self):
        covered = {n for branch in PARALLEL_BRANCHES for n in branch} | set(SEQUENTIAL_TAIL)
        assert covered == {
            "flight_research", "hotel_research", "places_research", "food_research",
            "transportation", "weather_season", "budget_optimizer", "itinerary_generator",
        }

    def test_real_branches_are_equal_length(self):
        # compute_replan_targets' safety relies on this: both parallel
        # branches in the real graph are exactly 2 nodes long, so
        # normalizing to branch roots always yields equal-depth targets.
        assert all(len(branch) == 2 for branch in PARALLEL_BRANCHES)


class _JoinState(TypedDict, total=False):
    val_a1: int
    val_a2: int
    val_b1: int
    val_b2: int
    joined: int
    targets: list
    calls: Annotated[list, operator.add]


async def _a1(state):
    return {"val_a1": 1, "calls": ["a1"]}


async def _a2(state):
    return {"val_a2": 1, "calls": ["a2"]}


async def _b1(state):
    return {"val_b1": 1, "calls": ["b1"]}


async def _b2(state):
    return {"val_b2": 1, "calls": ["b2"]}


async def _join(state):
    return {"joined": state.get("val_a2", 0) + state.get("val_b2", 0), "calls": ["join"]}


async def _dispatch(state):
    return {}


def _route(state):
    return state["targets"]


def _build_asymmetric_graph():
    """branch A is 2 hops to the join; branch B is 1 hop -- mirrors what
    happens if you reenter one real branch at its 2nd node while entering
    the other at its 1st node."""
    g = StateGraph(_JoinState)
    g.add_node("dispatch", _dispatch)
    g.add_node("a1", _a1)
    g.add_node("a2", _a2)
    g.add_node("b1", _b1)
    g.add_node("join", _join)
    g.add_edge(START, "dispatch")
    g.add_conditional_edges("dispatch", _route, {"a1": "a1", "a2": "a2", "b1": "b1"})
    g.add_edge("a1", "a2")
    g.add_edge("a2", "join")
    g.add_edge("b1", "join")
    return g.compile(checkpointer=MemorySaver())


def _build_symmetric_graph():
    """Both branches are 2 hops to the join -- mirrors the real graph's
    actual shape and what compute_replan_targets produces."""
    g = StateGraph(_JoinState)
    g.add_node("dispatch", _dispatch)
    g.add_node("a1", _a1)
    g.add_node("a2", _a2)
    g.add_node("b1", _b1)
    g.add_node("b2", _b2)
    g.add_node("join", _join)
    g.add_edge(START, "dispatch")
    g.add_conditional_edges("dispatch", _route, {"a1": "a1", "b1": "b1"})
    g.add_edge("a1", "a2")
    g.add_edge("a2", "join")
    g.add_edge("b1", "b2")
    g.add_edge("b2", "join")
    return g.compile(checkpointer=MemorySaver())


class TestLangGraphFanInSemantics:
    """Characterization tests documenting the underlying LangGraph behavior
    that motivates compute_replan_targets' branch-root normalization."""

    @pytest.mark.asyncio
    async def test_join_fires_once_when_only_one_branch_targeted(self):
        graph = _build_asymmetric_graph()
        result = await graph.ainvoke({"targets": ["b1"]}, {"configurable": {"thread_id": "single"}})
        assert result["calls"].count("join") == 1

    @pytest.mark.asyncio
    async def test_asymmetric_depth_without_normalization_double_fires(self):
        graph = _build_asymmetric_graph()
        # a1 (2 hops to join) and b1 (1 hop to join) targeted together --
        # exactly the shape compute_replan_targets exists to avoid.
        result = await graph.ainvoke({"targets": ["a1", "b1"]}, {"configurable": {"thread_id": "asymmetric"}})
        assert result["calls"].count("join") == 2  # documents the bug this way causes

    @pytest.mark.asyncio
    async def test_symmetric_depth_fires_once(self):
        graph = _build_symmetric_graph()
        # a1 and b1 are both branch roots, both 2 hops from the join --
        # this is what compute_replan_targets guarantees for the real graph.
        result = await graph.ainvoke({"targets": ["a1", "b1"]}, {"configurable": {"thread_id": "symmetric"}})
        assert result["calls"].count("join") == 1
        assert result["joined"] == 2
