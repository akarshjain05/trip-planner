from __future__ import annotations

import operator
from typing import Annotated, TypedDict

def merge_completed(left: list[str] | None, right: list[str] | None) -> list[str]:
    left = left or []
    right = right or []
    if right == ["__RESET__"]:
        return []
    if right and right[0] == "__RESET__":
        return list(set(right[1:]))
    return list(set(left + right))

class TripState(TypedDict, total=False):
    trip_id: str
    agent_run_id: str
    trigger: str
    start_time: float

    user_message: str
    conversation: list[dict]

    requirements: dict
    missing_info: dict
    awaiting_input: bool

    destination_result: dict
    destination: str
    research_sources: list[dict]
    flights: list[dict]
    hotels: list[dict]
    places: list[dict]
    restaurants: list[dict]
    transportation_plan: dict
    weather: dict
    budget: dict
    itinerary: dict

    critic_result: dict
    revisions: list[dict]
    iteration_count: int
    max_iterations: int
    replan_target: list[str]

    modification_result: dict

    tool_call_count: Annotated[int, operator.add]
    input_tokens: Annotated[int, operator.add]
    output_tokens: Annotated[int, operator.add]
    estimated_cost_usd: Annotated[float, operator.add]
    final: bool
    error: str | None

    completed_nodes: Annotated[list[str], merge_completed]


NODE_ORDER: list[str] = [
    "requirement_extractor",
    "missing_info_checker",
    "destination_research",
    "flight_research",
    "hotel_research",
    "places_research",
    "food_research",
    "transportation",
    "weather_season",
    "budget_optimizer",
    "itinerary_generator",
    "critic",
    "replanner",
    "finalize",
]

DEPENDENCIES = {
    "requirement_extractor": [],
    "missing_info_checker": ["requirement_extractor"],
    "destination_research": ["missing_info_checker"],
    "flight_research": ["destination_research"],
    "hotel_research": ["destination_research"],
    "places_research": ["flight_research"],
    "food_research": ["hotel_research"],
    "transportation": ["places_research", "food_research"],
    "weather_season": ["destination_research"],
    "budget_optimizer": ["flight_research", "hotel_research", "places_research", "food_research", "transportation"],
    "itinerary_generator": ["budget_optimizer", "weather_season"],
    "critic": ["itinerary_generator"],
    "replanner": [],
    "finalize": [],
}

def get_transitive_dependents(nodes: list[str]) -> set[str]:
    dependents = set()
    rev_deps = {n: [] for n in DEPENDENCIES}
    for node, deps in DEPENDENCIES.items():
        for d in deps:
            if d in rev_deps:
                rev_deps[d].append(node)
    
    queue = list(nodes)
    while queue:
        current = queue.pop(0)
        for dep in rev_deps.get(current, []):
            if dep not in dependents:
                dependents.add(dep)
                queue.append(dep)
    return dependents
