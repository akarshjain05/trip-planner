"""
The LangGraph state schema.

This is deliberately a plain, JSON-serializable TypedDict: every node reads
some subset of these keys and returns a partial dict of the keys it wrote.
Because state persists across the whole run, node N's output becomes node
N+1's input by construction -- there is no separate "pass the result along"
plumbing to get wrong.

Nodes do NOT talk to the database or Redis directly (except via the
`emit` dependency injected at graph-build time for progress events) --
they are pure functions over this state, which is what makes them cheap
to unit test (see backend/tests/test_agent_nodes.py).
"""
from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class TripState(TypedDict, total=False):
    # --- identity / control ---
    trip_id: str
    agent_run_id: str
    trigger: str  # "initial_plan" | "modification"

    # --- conversation ---
    user_message: str
    conversation: list[dict]

    # --- requirement extraction ---
    requirements: dict  # TripRequirements.model_dump()
    missing_info: dict  # MissingInfoResult.model_dump()
    awaiting_input: bool

    # --- research results (each a list[dict] of the matching domain model) ---
    destination_result: dict  # DestinationResearchResult.model_dump()
    destination: str
    research_sources: list[dict]  # web-search provenance (section 9): url/title/source/facts/confidence
    flights: list[dict]
    hotels: list[dict]
    places: list[dict]
    restaurants: list[dict]
    transportation_plan: dict
    weather: dict
    budget: dict
    itinerary: dict

    # --- critic / replanning ---
    critic_result: dict
    revisions: list[dict]
    iteration_count: int
    max_iterations: int
    replan_target: list[str]  # earliest node name(s) to resume from, one per affected branch

    # --- modification ---
    modification_result: dict

    # --- bookkeeping (accumulators -- parallel branches may both write in
    # the same step, so these use a reducer and nodes emit *deltas*, not
    # running totals) ---
    tool_call_count: Annotated[int, operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
    estimated_cost_usd: Annotated[float, operator.add]
    final: bool
    error: str | None


NODE_ORDER: list[str] = [
    "destination_research",
    "flight_research",
    "hotel_research",
    "places_research",
    "food_research",
    "transportation",
    "weather_season",
    "budget_optimizer",
    "itinerary_generator",
]

# The graph has two independent parallel chains between destination_research
# and the transportation join (see app/agents/graph.py). Replanning must
# pick a reentry point *per branch* -- a single globally-earliest node would
# silently starve whichever branch it doesn't belong to (verified against
# LangGraph's actual fan-in behavior: a join fires as soon as any one
# predecessor completes, using the *other* branch's last-known state, which
# is exactly what would let a still-needed fix go unapplied).
PARALLEL_BRANCHES: list[list[str]] = [
    ["flight_research", "places_research"],
    ["hotel_research", "food_research"],
]
SEQUENTIAL_TAIL: list[str] = ["transportation", "weather_season", "budget_optimizer", "itinerary_generator"]


def compute_replan_targets(recommended: list[str]) -> list[str]:
    """Given the (possibly cross-branch) set of node names that need to
    rerun, return the minimal set of reentry points.

    Two subtleties, both verified empirically against LangGraph's actual
    execution model (see backend/tests/test_graph_topology.py):

    1. A join fires as soon as ANY one predecessor completes, using
       whatever the OTHER predecessor's state currently holds -- so
       targeting only one branch when only that branch needs work is safe
       and does not deadlock.
    2. If TWO OR MORE branches are targeted in the SAME replan (because
       both need work), they must reenter at the SAME depth (their branch
       root), not at whichever node specifically needs rework -- otherwise
       the shorter branch reaches the join first, the join fires early on
       stale data from the still-running branch, and then fires AGAIN when
       the slower branch finishes, double-executing everything downstream.
    """
    recommended_set = {n for n in recommended if n in NODE_ORDER}
    branches_with_hits = [
        (branch, [n for n in branch if n in recommended_set])
        for branch in PARALLEL_BRANCHES
    ]
    branches_with_hits = [(b, h) for b, h in branches_with_hits if h]

    targets: list[str] = []
    if len(branches_with_hits) >= 2:
        targets = [branch[0] for branch, _hits in branches_with_hits]
    elif len(branches_with_hits) == 1:
        branch, hits = branches_with_hits[0]
        targets = [min(hits, key=branch.index)]

    if not targets:
        tail_hits = [n for n in SEQUENTIAL_TAIL if n in recommended_set]
        if tail_hits:
            targets.append(min(tail_hits, key=SEQUENTIAL_TAIL.index))

    return targets or ["itinerary_generator"]
