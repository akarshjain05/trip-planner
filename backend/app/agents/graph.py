"""
Wires every node from app/agents/nodes/ into the StateGraph from the spec's
own architecture diagram (section 3):

    dispatch -> requirement_extractor -> missing_info_checker
        -[missing]-> END (awaiting_input)
        -[ok]-> destination_research
                    -> {flight_research, hotel_research}   (parallel)
                    -> flight_research -> places_research
                    -> hotel_research  -> food_research
                    -> {places_research, food_research} join at transportation
                    -> transportation -> weather_season -> budget_optimizer
                    -> itinerary_generator -> critic
                        -[approved or max_iterations]-> finalize -> END
                        -[rejected]-> replanner -> (earliest affected node) -> ... -> critic

A user modification is resolved to a `replan_target` *before* invocation
(see trip_service.py) and enters through the same `dispatch` node, so the
critic loop and user-driven partial replanning share one code path.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.deps import NodeDeps
from app.agents.nodes.budget import make_budget_optimizer_node
from app.agents.nodes.critic import (
    make_critic_node,
    make_finalize_node,
    make_replanner_node,
    route_after_critic,
    route_after_replanner,
)
from app.agents.nodes.destination import make_destination_research_node
from app.agents.nodes.dispatch import dispatch_node, route_dispatch
from app.agents.nodes.flights import make_flight_research_node
from app.agents.nodes.food import make_food_research_node
from app.agents.nodes.hotels import make_hotel_research_node
from app.agents.nodes.itinerary import make_itinerary_generator_node
from app.agents.nodes.places import make_places_research_node
from app.agents.nodes.requirements import (
    make_missing_info_checker_node,
    make_requirement_extractor_node,
    route_after_missing_info,
)
from app.agents.nodes.transportation import make_transportation_node
from app.agents.nodes.weather import make_weather_season_node
from app.agents.state import NODE_ORDER, TripState


def build_trip_graph(deps: NodeDeps):
    graph = StateGraph(TripState)

    graph.add_node("dispatch", dispatch_node)
    graph.add_node("requirement_extractor", make_requirement_extractor_node(deps))
    graph.add_node("missing_info_checker", make_missing_info_checker_node(deps))
    graph.add_node("destination_research", make_destination_research_node(deps))
    graph.add_node("flight_research", make_flight_research_node(deps))
    graph.add_node("hotel_research", make_hotel_research_node(deps))
    graph.add_node("places_research", make_places_research_node(deps))
    graph.add_node("food_research", make_food_research_node(deps))
    graph.add_node("transportation", make_transportation_node(deps))
    graph.add_node("weather_season", make_weather_season_node(deps))
    graph.add_node("budget_optimizer", make_budget_optimizer_node(deps))
    graph.add_node("itinerary_generator", make_itinerary_generator_node(deps))
    graph.add_node("critic", make_critic_node(deps))
    graph.add_node("replanner", make_replanner_node(deps))
    graph.add_node("finalize", make_finalize_node(deps))

    graph.add_edge(START, "dispatch")
    # Dispatch can send execution to requirement_extractor (normal / resume)
    # or directly to any pipeline node (user-driven partial replan).
    graph.add_conditional_edges("dispatch", route_dispatch, {**{n: n for n in NODE_ORDER}, "requirement_extractor": "requirement_extractor"})

    graph.add_edge("requirement_extractor", "missing_info_checker")
    graph.add_conditional_edges("missing_info_checker", route_after_missing_info, {END: END, "destination_research": "destination_research"})

    # Parallel fan-out: flights and hotels are independent research branches.
    graph.add_edge("destination_research", "flight_research")
    graph.add_edge("destination_research", "hotel_research")
    graph.add_edge("flight_research", "places_research")
    graph.add_edge("hotel_research", "food_research")
    # Fan-in / join: transportation waits for both branches.
    graph.add_edge("places_research", "transportation")
    graph.add_edge("food_research", "transportation")

    graph.add_edge("transportation", "weather_season")
    graph.add_edge("weather_season", "budget_optimizer")
    graph.add_edge("budget_optimizer", "itinerary_generator")
    graph.add_edge("itinerary_generator", "critic")

    graph.add_conditional_edges("critic", route_after_critic, {"finalize": "finalize", "replanner": "replanner"})
    graph.add_conditional_edges("replanner", route_after_replanner, {n: n for n in NODE_ORDER})
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=MemorySaver())
