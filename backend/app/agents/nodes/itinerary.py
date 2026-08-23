from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import (
    BudgetBreakdown, FlightOptionModel, HotelOptionModel, ItineraryModel, PlaceModel,
    RestaurantModel, TransportationPlan, TripRequirements, WeatherOutlook,
)


def make_itinerary_generator_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "itinerary_generator", "Assembling your day-by-day itinerary...")
        req = TripRequirements(**state["requirements"])
        flights = [FlightOptionModel(**f) for f in state.get("flights", [])]
        hotels = [HotelOptionModel(**h) for h in state.get("hotels", [])]
        places = [PlaceModel(**p) for p in state.get("places", [])]
        restaurants = [RestaurantModel(**r) for r in state.get("restaurants", [])]
        weather = WeatherOutlook(**state["weather"])
        budget = BudgetBreakdown(**state["budget"])
        transportation = TransportationPlan(**state["transportation_plan"]) if state.get("transportation_plan") else None
        destination = state.get("destination") or req.destination or "your destination"

        result = await deps.orchestrator.generate_itinerary(
            req, destination, flights, hotels, places, restaurants, weather, budget, transportation
        )
        itinerary: ItineraryModel = result.value

        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed", "itinerary_generator",
                         f"Drafted a {len(itinerary.days)}-day itinerary.", {"days": len(itinerary.days)})
        return {"itinerary": itinerary.model_dump(mode="json"), **usage_update(state, result.usage)}
    return node
