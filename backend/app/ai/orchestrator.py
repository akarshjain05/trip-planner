"""
The one class every agent node talks to for LLM-backed reasoning.

Each public method corresponds to exactly one node's job and returns a
validated Pydantic object (never raw text). Internally it either:
  (a) calls the configured real chat model with structured output, or
  (b) calls the deterministic mock in app/ai/mock_llm.py

...based on Settings.use_mock_llm. Nodes never know or care which path ran;
they just get a typed object back plus a UsageInfo they log for cost
tracking. This is what "swap the model from .env" and "runs with zero
API keys" both cash out to in code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel

from app.ai import mock_llm
from app.ai.factory import build_chat_model
from app.agents.prompts import load_prompt
from app.core.config import Settings
from app.schemas.domain import (
    BudgetBreakdown,
    CriticResult,
    DestinationResearchResult,
    FlightOptionModel,
    HotelOptionModel,
    ItineraryModel,
    MissingInfoResult,
    ModificationInterpretation,
    PlaceModel,
    RestaurantModel,
    TransportationPlan,
    TripRequirements,
    WeatherOutlook,
)

T = TypeVar("T", bound=BaseModel)


@dataclass
class UsageInfo:
    input_tokens: int = 0
    output_tokens: int = 0
    used_mock: bool = True
    estimated_cost_usd: float = 0.0


@dataclass
class LLMResult:
    value: object
    usage: UsageInfo = field(default_factory=UsageInfo)


# Rough $/1K token estimates for cost display only -- not billing-accurate.
_COST_PER_1K_INPUT = 0.005
_COST_PER_1K_OUTPUT = 0.015


class LLMOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._chat_model = None if settings.use_mock_llm else build_chat_model(settings)

    # -- internal helper: real structured call with usage tracking --------
    async def _structured(self, schema_cls: type[T], system_prompt: str, user_prompt: str) -> LLMResult:
        if self._chat_model is None:
            raise RuntimeError("Real LLM requested but orchestrator is in mock mode.")
        structured_model = self._chat_model.with_structured_output(schema_cls, include_raw=True)
        result = await structured_model.ainvoke(
            [("system", system_prompt), ("human", user_prompt)]
        )
        parsed = result["parsed"]
        raw = result.get("raw")
        usage_meta = getattr(raw, "usage_metadata", None) or {}
        in_tok = usage_meta.get("input_tokens", 0) or 0
        out_tok = usage_meta.get("output_tokens", 0) or 0
        cost = (in_tok / 1000) * _COST_PER_1K_INPUT + (out_tok / 1000) * _COST_PER_1K_OUTPUT
        return LLMResult(value=parsed, usage=UsageInfo(in_tok, out_tok, used_mock=False, estimated_cost_usd=cost))

    @staticmethod
    def _mock_result(value: object) -> LLMResult:
        return LLMResult(value=value, usage=UsageInfo(used_mock=True))

    # -- 1. Requirement extraction -----------------------------------------
    async def extract_requirements(
        self, message: str, base: TripRequirements | None = None, expected_fields: list[str] | None = None
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.extract_requirements(message, base, expected_fields))
        prompt = load_prompt("requirement_extractor")
        context = (
            f"Prior known requirements: {base.model_dump_json() if base else '{}'}\n"
            f"Fields the user was just asked for: {expected_fields or []}\n\n"
            f"User message: {message}"
        )
        return await self._structured(TripRequirements, prompt, context)

    async def check_missing_info(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.check_missing_info(req))
        prompt = load_prompt("missing_info_checker")
        return await self._structured(MissingInfoResult, prompt, req.model_dump_json())

    # -- 2. Destination research --------------------------------------------
    async def research_destinations(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.research_destinations(req))
        prompt = load_prompt("destination_research")
        return await self._structured(DestinationResearchResult, prompt, req.model_dump_json())

    # -- 3. Ranking already-fetched provider results ------------------------
    async def rank_flights(self, req: TripRequirements, options: list[FlightOptionModel], prioritize_cost: bool = False) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_flights(req, options, prioritize_cost))
        prompt = load_prompt("flight_research")
        ctx = f"Requirements: {req.model_dump_json()}\nOptions: {[o.model_dump() for o in options]}"

        class _Selection(BaseModel):
            selected: list[FlightOptionModel]

        result = await self._structured(_Selection, prompt, ctx)
        result.value = result.value.selected
        return result

    async def rank_hotels(self, req: TripRequirements, options: list[HotelOptionModel]) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_hotels(req, options))
        prompt = load_prompt("hotel_research")
        ctx = f"Requirements: {req.model_dump_json()}\nOptions: {[o.model_dump() for o in options]}"

        class _Selection(BaseModel):
            selected: list[HotelOptionModel]

        result = await self._structured(_Selection, prompt, ctx)
        result.value = result.value.selected
        return result

    async def rank_places(self, req: TripRequirements, options: list[PlaceModel], relax_crowd_filter: bool = False) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_places(req, options, relax_crowd_filter))
        prompt = load_prompt("activity_research")
        ctx = f"Requirements: {req.model_dump_json()}\nOptions: {[o.model_dump() for o in options]}"

        class _Selection(BaseModel):
            selected: list[PlaceModel]

        result = await self._structured(_Selection, prompt, ctx)
        result.value = result.value.selected
        return result

    async def rank_restaurants(self, req: TripRequirements, options: list[RestaurantModel]) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_restaurants(req, options))
        prompt = load_prompt("food_research")
        ctx = f"Requirements: {req.model_dump_json()}\nOptions: {[o.model_dump() for o in options]}"

        class _Selection(BaseModel):
            selected: list[RestaurantModel]

        result = await self._structured(_Selection, prompt, ctx)
        result.value = result.value.selected
        return result

    # -- 4. Transportation / weather ----------------------------------------
    async def plan_transportation(self, req: TripRequirements, hotel: HotelOptionModel | None) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.plan_transportation(req, hotel))
        prompt = load_prompt("transportation")
        ctx = f"Requirements: {req.model_dump_json()}\nHotel: {hotel.model_dump() if hotel else None}"
        return await self._structured(TransportationPlan, prompt, ctx)

    async def weather_outlook(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.weather_outlook(req))
        prompt = load_prompt("weather_season")
        return await self._structured(WeatherOutlook, prompt, req.model_dump_json())

    # -- 5. Budget ------------------------------------------------------------
    async def optimize_budget(
        self, req: TripRequirements, flights: list[FlightOptionModel], hotels: list[HotelOptionModel],
        places: list[PlaceModel], restaurants: list[RestaurantModel],
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.optimize_budget(req, flights, hotels, places, restaurants))
        prompt = load_prompt("budget_optimizer")
        ctx = (
            f"Requirements: {req.model_dump_json()}\nFlights: {[f.model_dump() for f in flights]}\n"
            f"Hotels: {[h.model_dump() for h in hotels]}\nPlaces: {[p.model_dump() for p in places]}\n"
            f"Restaurants: {[r.model_dump() for r in restaurants]}"
        )
        return await self._structured(BudgetBreakdown, prompt, ctx)

    # -- 6. Itinerary -----------------------------------------------------------
    async def generate_itinerary(
        self, req: TripRequirements, destination: str, flights: list[FlightOptionModel],
        hotels: list[HotelOptionModel], places: list[PlaceModel], restaurants: list[RestaurantModel],
        weather: WeatherOutlook, budget: BudgetBreakdown, transportation: TransportationPlan | None = None,
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(
                mock_llm.generate_itinerary(req, destination, flights, hotels, places, restaurants, weather, budget, transportation)
            )
        prompt = load_prompt("itinerary_generator")
        ctx = (
            f"Requirements: {req.model_dump_json()}\nDestination: {destination}\n"
            f"Flights: {[f.model_dump() for f in flights]}\nHotels: {[h.model_dump() for h in hotels]}\n"
            f"Places: {[p.model_dump() for p in places]}\nRestaurants: {[r.model_dump() for r in restaurants]}\n"
            f"Transportation: {transportation.model_dump_json() if transportation else '{}'}\n"
            f"Weather: {weather.model_dump_json()}\nBudget: {budget.model_dump_json()}"
        )
        return await self._structured(ItineraryModel, prompt, ctx)

    # -- 7. Critic --------------------------------------------------------------
    async def critic_review(
        self, req: TripRequirements, itinerary: ItineraryModel, budget: BudgetBreakdown, places: list[PlaceModel],
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.critic_review(req, itinerary, budget, places))
        prompt = load_prompt("critic")
        ctx = (
            f"Requirements: {req.model_dump_json()}\nItinerary: {itinerary.model_dump_json()}\n"
            f"Budget: {budget.model_dump_json()}"
        )
        return await self._structured(CriticResult, prompt, ctx)

    # -- 8. Conversational modification -----------------------------------------
    async def interpret_modification(self, message: str, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.interpret_modification(message, req))
        prompt = load_prompt("modification_interpreter")
        ctx = f"Current requirements: {req.model_dump_json()}\nUser message: {message}"
        return await self._structured(ModificationInterpretation, prompt, ctx)
