from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.deps import NodeDeps
from app.agents.nodes.budget import make_budget_optimizer_node
from app.agents.nodes.critic import (
    make_critic_node,
    make_finalize_node,
    make_replanner_node,
)
from app.agents.nodes.destination import make_destination_research_node
from app.agents.nodes.flights import make_flight_research_node
from app.agents.nodes.food import make_food_research_node
from app.agents.nodes.hotels import make_hotel_research_node
from app.agents.nodes.itinerary import make_itinerary_generator_node
from app.agents.nodes.places import make_places_research_node
from app.agents.nodes.requirements import (
    make_missing_info_checker_node,
    make_requirement_extractor_node,
)
from app.agents.nodes.scheduler import scheduler_node, route_scheduler
from app.agents.nodes.transportation import make_transportation_node
from app.agents.nodes.weather import make_weather_season_node
from app.agents.state import NODE_ORDER, TripState


def build_trip_graph(deps: NodeDeps):
    graph = StateGraph(TripState)

    from opentelemetry import trace
    tracer = trace.get_tracer(__name__)

    async def wrapped_scheduler(state: TripState):
        with tracer.start_as_current_span("scheduler") as span:
            span.set_attribute("node.name", "scheduler")
            return scheduler_node(state)

    graph.add_node("scheduler", wrapped_scheduler)
    
    def wrap_node(name, node_func):
        async def wrapper(state: TripState):
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("node.name", name)
                result = await node_func(state)
                if result is None:
                    result = {}
                result["completed_nodes"] = [name]
                return result
        return wrapper

    graph.add_node("requirement_extractor", wrap_node("requirement_extractor", make_requirement_extractor_node(deps)))
    graph.add_node("missing_info_checker", wrap_node("missing_info_checker", make_missing_info_checker_node(deps)))
    graph.add_node("destination_research", wrap_node("destination_research", make_destination_research_node(deps)))
    graph.add_node("flight_research", wrap_node("flight_research", make_flight_research_node(deps)))
    graph.add_node("hotel_research", wrap_node("hotel_research", make_hotel_research_node(deps)))
    graph.add_node("places_research", wrap_node("places_research", make_places_research_node(deps)))
    graph.add_node("food_research", wrap_node("food_research", make_food_research_node(deps)))
    graph.add_node("transportation", wrap_node("transportation", make_transportation_node(deps)))
    graph.add_node("weather_season", wrap_node("weather_season", make_weather_season_node(deps)))
    graph.add_node("budget_optimizer", wrap_node("budget_optimizer", make_budget_optimizer_node(deps)))
    graph.add_node("itinerary_generator", wrap_node("itinerary_generator", make_itinerary_generator_node(deps)))
    graph.add_node("critic", wrap_node("critic", make_critic_node(deps)))
    graph.add_node("replanner", wrap_node("replanner", make_replanner_node(deps)))
    graph.add_node("finalize", wrap_node("finalize", make_finalize_node(deps)))

    graph.add_edge(START, "scheduler")
    
    graph.add_conditional_edges(
        "scheduler", 
        route_scheduler, 
        [n for n in NODE_ORDER] + [END]
    )

    for node in NODE_ORDER:
        graph.add_edge(node, "scheduler")

    return graph.compile(checkpointer=MemorySaver())
