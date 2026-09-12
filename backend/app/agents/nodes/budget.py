from __future__ import annotations
from app.agents.deps import NodeDeps
from app.agents.nodes._common import usage_update
from app.agents.state import TripState
from app.schemas.domain import (
    BudgetBreakdown, FlightOptionModel, HotelOptionModel, PlaceModel, RestaurantModel, TripRequirements,
)


def make_budget_optimizer_node(deps: NodeDeps):
    async def node(state: TripState) -> dict:
        await deps.emit(state["trip_id"], state["agent_run_id"], "agent_started",
                         "budget_optimizer", "Building the budget and checking it against your limit...")
        req = TripRequirements(**state["requirements"])
        flights = [FlightOptionModel(**f) for f in state.get("flights", [])]
        hotels = [HotelOptionModel(**h) for h in state.get("hotels", [])]
        places = [PlaceModel(**p) for p in state.get("places", [])]
        restaurants = [RestaurantModel(**r) for r in state.get("restaurants", [])]

        result = await deps.orchestrator.optimize_budget(req, flights, hotels, places, restaurants)
        budget: BudgetBreakdown = result.value

        target_currency = req.budget_currency or budget.currency or "USD"
        budget.currency = target_currency.upper()
        total = 0.0
        
        for line in budget.lines:
            if line.currency and line.currency.upper() != target_currency.upper():
                try:
                    rate = await deps.currency_provider.get_rate(line.currency.upper(), target_currency.upper())
                    line.estimated_amount = round(line.estimated_amount * rate, 2)
                    line.currency = target_currency.upper()
                except Exception as e:
                    pass
            total += line.estimated_amount
            
        # Convert flights and hotels in the state so the itinerary generator has the exact costs
        for f in flights:
            if f.currency and f.currency.upper() != target_currency.upper():
                try:
                    rate = await deps.currency_provider.get_rate(f.currency.upper(), target_currency.upper())
                    f.price = round(f.price * rate, 2)
                    f.currency = target_currency.upper()
                except Exception as e:
                    from app.core.logging import get_logger
                    get_logger(__name__).warning("budget_currency_conversion_failed", provider=f.provider, error=str(e))

        for h in hotels:
            if h.currency and h.currency.upper() != target_currency.upper():
                try:
                    rate = await deps.currency_provider.get_rate(h.currency.upper(), target_currency.upper())
                    h.price_per_night = round(h.price_per_night * rate, 2)
                    h.currency = target_currency.upper()
                except Exception as e:
                    from app.core.logging import get_logger
                    get_logger(__name__).warning("budget_currency_conversion_failed", provider=h.provider, error=str(e))

        budget.total_estimated = round(total, 2)

        msg = f"Estimated total: {budget.total_estimated:.0f} {budget.currency}."
        if budget.optimizations_applied:
            msg += f" Applied {len(budget.optimizations_applied)} optimization(s) to fit your budget."
        elif budget.over_budget:
            msg += f" Still over budget by {budget.over_budget_by:.0f} {budget.currency}."

        await deps.emit(state["trip_id"], state["agent_run_id"], "budget_updated", "budget_optimizer", msg,
                         {"total_estimated": budget.total_estimated, "over_budget": budget.over_budget,
                          "optimizations_applied": budget.optimizations_applied})
        return {
            "budget": budget.model_dump(mode="json"),
            "flights": [f.model_dump(mode="json") for f in flights],
            "hotels": [h.model_dump(mode="json") for h in hotels],
            **usage_update(state, result.usage)
        }
    return node
