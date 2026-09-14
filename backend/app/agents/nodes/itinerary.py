from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import (
    BudgetBreakdown, FlightOptionModel, HotelOptionModel, ItineraryModel, PlaceModel,
    RestaurantModel, TransportationPlan, TripRequirements, WeatherOutlook,
)


# ---------------------------------------------------------------------------
# Realistic cost defaults by activity type (in USD).
# These are conservative mid-range estimates used ONLY when the LLM returns
# null for estimated_cost.  They act as a safety net so the UI always shows
# a price.
# ---------------------------------------------------------------------------
_DEFAULT_COSTS_USD: dict[str, float] = {
    "meal":           25.0,   # per-person casual dining
    "attraction":     15.0,   # average museum / park entry
    "transfer":       20.0,   # taxi / shuttle
    "hotel_checkin":   0.0,   # filled separately from hotel data
    "hotel_checkout":  0.0,
    "free_time":       0.0,
    "flight":          0.0,   # should already come from flight data
    "other":           0.0,
}


def _backfill_costs(
    itinerary: ItineraryModel,
    hotels: list[HotelOptionModel],
    travelers: int,
    duration_days: int,
    usd_rate: float = 1.0,
) -> None:
    """Mutate *itinerary* in-place so every activity has a non-null
    estimated_cost.  Hotel check-in gets total_nights × price_per_night;
    meals get multiplied by traveler count; everything else gets a
    sensible default.  All USD defaults are converted via *usd_rate*."""

    hotel_total = 0.0
    if hotels:
        best = hotels[0]
        hotel_total = best.price_per_night * max(duration_days - 1, 1)

    for day in itinerary.days:
        for act in day.activities:
            if act.estimated_cost is not None and act.estimated_cost > 0:
                continue  # LLM already filled it with a non-zero value — don't override

            if act.activity_type == "hotel_checkin":
                act.estimated_cost = round(hotel_total, 2)
            elif act.activity_type == "meal":
                act.estimated_cost = round(
                    _DEFAULT_COSTS_USD["meal"] * travelers * usd_rate, 2
                )
            elif act.activity_type == "attraction":
                act.estimated_cost = round(
                    _DEFAULT_COSTS_USD["attraction"] * usd_rate, 2
                )
            elif act.activity_type == "transfer":
                act.estimated_cost = round(
                    _DEFAULT_COSTS_USD["transfer"] * usd_rate, 2
                )
            else:
                act.estimated_cost = 0.0

    # Recompute total
    itinerary.total_estimated_cost = round(
        sum(
            act.estimated_cost or 0.0
            for day in itinerary.days
            for act in day.activities
        ),
        2,
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

        # --- Fetch USD → user-currency rate for backfill defaults ---------
        target_currency = (req.budget_currency or "INR").upper()
        usd_rate = 1.0
        if target_currency != "USD":
            try:
                usd_rate = await deps.currency_provider.get_rate("USD", target_currency)
            except Exception:
                usd_rate = 1.0  # fallback: leave as USD

        # --- Safety net: fill any null costs the LLM missed ---------------
        _backfill_costs(
            itinerary,
            hotels,
            travelers=req.travelers or 1,
            duration_days=req.duration_days or len(itinerary.days),
            usd_rate=usd_rate,
        )

        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_completed", "itinerary_generator",
                         f"Drafted a {len(itinerary.days)}-day itinerary.", {"days": len(itinerary.days)})
        return {"itinerary": itinerary.model_dump(mode="json"), **usage_update(state, result.usage)}
    return node
