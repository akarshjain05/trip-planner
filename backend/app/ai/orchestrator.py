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


from app.ai.provider_pool import ProviderPool

class LLMOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._pool = None if settings.use_mock_llm else ProviderPool(settings)

    # -- internal helper: real structured call with usage tracking --------
    async def _structured(self, schema_cls: type[T], system_prompt: str, user_prompt: str, cheap: bool = False) -> LLMResult:
        if self._pool is None:
            raise RuntimeError("Real LLM requested but orchestrator is in mock mode.")

        import hashlib
        import json
        from app.tools.cache import cached, make_cache_key
        from langchain_core.messages import HumanMessage, SystemMessage

        schema_hash = hashlib.sha256(
            json.dumps(schema_cls.model_json_schema(), sort_keys=True).encode()
        ).hexdigest()[:12]
        
        cache_key = make_cache_key(
            "llm_call", schema=schema_cls.__name__, schema_hash=schema_hash,
            chain=",".join(self.settings.llm_provider_chain), 
            cheap=cheap,
            system_prompt=system_prompt, user_prompt=user_prompt,
        )

        async def fetch() -> dict:
            parsed, raw, provider_used, model_used = await self._pool.ainvoke_structured(
                schema_cls, [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)], cheap=cheap
            )
            usage_meta = getattr(raw, "usage_metadata", None) or {}
            return {
                "value": parsed.model_dump(mode="json"),
                "input_tokens": usage_meta.get("input_tokens", 0) or 0,
                "output_tokens": usage_meta.get("output_tokens", 0) or 0,
            }

        cached_payload, hit = await cached(cache_key, self.settings.CACHE_TTL_LLM, fetch)
        value = schema_cls(**cached_payload["value"])

        if hit:
            usage = UsageInfo(input_tokens=0, output_tokens=0, used_mock=False, estimated_cost_usd=0.0)
        else:
            in_tok, out_tok = cached_payload["input_tokens"], cached_payload["output_tokens"]
            # Estimate cost (very rough)
            cost = (in_tok / 1000) * 0.001 + (out_tok / 1000) * 0.002
            usage = UsageInfo(input_tokens=in_tok, output_tokens=out_tok, used_mock=False, estimated_cost_usd=cost)

        return LLMResult(value=value, usage=usage)

    @staticmethod
    def _mock_result(value: object) -> LLMResult:
        return LLMResult(value=value, usage=UsageInfo(used_mock=True))


    async def _with_fallback(self, real_coro_factory, mock_value_factory, node_name: str) -> LLMResult:
        """Try the real LLM path; if the whole provider pool is exhausted (or
        any other pool-level failure happens), log it and fall back to the
        deterministic mock rather than failing the entire trip."""
        try:
            return await real_coro_factory()
        except Exception as e:
            from app.core.logging import get_logger
            get_logger("orchestrator").warning(
                "llm_fallback_to_mock", node=node_name, error=str(e)[:300]
            )
            return self._mock_result(mock_value_factory())

    # -- 1. Requirement extraction -----------------------------------------
    async def extract_requirements(self, message: str, base: TripRequirements | None = None, expected_fields: list[str] | None = None) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.extract_requirements(message, base, expected_fields))
        prompt = load_prompt("requirement_extractor")
        context = (
            f"Prior known requirements: {base.model_dump_json(exclude_none=True) if base else '{}'}\n"
            f"Fields the user was just asked for: {expected_fields or []}\n\n"
            f"User message: {message}"
        )
        return await self._with_fallback(
            lambda: self._structured(TripRequirements, prompt, context, cheap=True),
            lambda: mock_llm.extract_requirements(message, base, expected_fields),
            "requirement_extractor",
        )

    async def check_missing_info(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.check_missing_info(req))
        prompt = load_prompt("missing_info_checker")
        return await self._structured(MissingInfoResult, prompt, req.model_dump_json(exclude_none=True), cheap=True)

    # -- 2. Destination research --------------------------------------------
    async def research_destinations(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.research_destinations(req))
        prompt = load_prompt("destination_research")
        return await self._with_fallback(
            lambda: self._structured(DestinationResearchResult, prompt, req.model_dump_json(exclude_none=True), cheap=True),
            lambda: mock_llm.research_destinations(req),
            "destination_research",
        )


    # -- 3. Ranking already-fetched provider results ------------------------
    async def rank_flights(self, req: TripRequirements, options: list[FlightOptionModel], prioritize_cost: bool = False) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_flights(req, options, prioritize_cost))
        prompt = load_prompt("flight_research")
        candidates = sorted(options, key=lambda f: f.price or 999999)[:12]
        ctx = f"Requirements: {req.model_dump_json(exclude_none=True)}\nOptions: {[o.model_dump(exclude_none=True) for o in candidates]}"

        class _Selection(BaseModel):
            selected: list[FlightOptionModel]

        async def _real():
            result = await self._structured(_Selection, prompt, ctx, cheap=True)
            result.value = result.value.selected
            return result
        return await self._with_fallback(_real, lambda: mock_llm.rank_flights(req, options, prioritize_cost), "flight_research")

    async def rank_hotels(self, req: TripRequirements, options: list[HotelOptionModel]) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_hotels(req, options))
        prompt = load_prompt("hotel_research")
        candidates = sorted(options, key=lambda h: -(h.rating or 0))[:12]
        ctx = f"Requirements: {req.model_dump_json(exclude_none=True)}\nOptions: {[o.model_dump(exclude_none=True) for o in candidates]}"

        class _Selection(BaseModel):
            selected: list[HotelOptionModel]

        async def _real():
            result = await self._structured(_Selection, prompt, ctx, cheap=True)
            result.value = result.value.selected
            return result
        return await self._with_fallback(_real, lambda: mock_llm.rank_hotels(req, options), "hotel_research")

    async def rank_places(self, req: TripRequirements, options: list[PlaceModel], relax_crowd_filter: bool = False) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_places(req, options, relax_crowd_filter))
        prompt = load_prompt("activity_research")
        candidates = sorted(options, key=lambda p: -(p.rating or 0))[:12]
        ctx = f"Requirements: {req.model_dump_json(exclude_none=True)}\nOptions: {[o.model_dump(exclude_none=True) for o in candidates]}"

        class _Selection(BaseModel):
            selected: list[PlaceModel]

        async def _real():
            result = await self._structured(_Selection, prompt, ctx, cheap=True)
            result.value = result.value.selected
            return result
        return await self._with_fallback(_real, lambda: mock_llm.rank_places(req, options, relax_crowd_filter), "activity_research")

    async def rank_restaurants(self, req: TripRequirements, options: list[RestaurantModel]) -> LLMResult:
        if self.settings.use_mock_llm or not options:
            return self._mock_result(mock_llm.rank_restaurants(req, options))
        prompt = load_prompt("food_research")
        candidates = sorted(options, key=lambda r: -(r.rating or 0))[:12]
        ctx = f"Requirements: {req.model_dump_json(exclude_none=True)}\nOptions: {[o.model_dump(exclude_none=True) for o in candidates]}"

        class _Selection(BaseModel):
            selected: list[RestaurantModel]

        async def _real():
            result = await self._structured(_Selection, prompt, ctx, cheap=True)
            result.value = result.value.selected
            return result
        return await self._with_fallback(_real, lambda: mock_llm.rank_restaurants(req, options), "food_research")


    # -- 4. Transportation / weather ----------------------------------------
    async def plan_transportation(self, req: TripRequirements, hotel: HotelOptionModel | None) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.plan_transportation(req, hotel))
        prompt = load_prompt("transportation")
        ctx = f"Requirements: {req.model_dump_json(exclude_none=True)}\nHotel: {hotel.model_dump() if hotel else None}"
        return await self._with_fallback(
            lambda: self._structured(TransportationPlan, prompt, ctx, cheap=True),
            lambda: mock_llm.plan_transportation(req, hotel),
            "transportation",
        )

    async def weather_outlook(self, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.weather_outlook(req))
        prompt = load_prompt("weather_season")
        return await self._with_fallback(
            lambda: self._structured(WeatherOutlook, prompt, req.model_dump_json(exclude_none=True), cheap=True),
            lambda: mock_llm.weather_outlook(req),
            "weather_season",
        )


    # -- 5. Budget ------------------------------------------------------------
    async def optimize_budget(
        self, req: TripRequirements, flights: list[FlightOptionModel], hotels: list[HotelOptionModel],
        places: list[PlaceModel], restaurants: list[RestaurantModel],
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.optimize_budget(req, flights, hotels, places, restaurants))
        prompt = load_prompt("budget_optimizer")
        ctx = (
            f"Requirements: {req.model_dump_json(exclude_none=True)}\nFlights: {[f.model_dump(exclude_none=True) for f in flights]}\n"
            f"Hotels: {[h.model_dump(exclude_none=True) for h in hotels]}\nPlaces: {[p.model_dump(exclude_none=True) for p in places]}\n"
            f"Restaurants: {[r.model_dump(exclude_none=True) for r in restaurants]}"
        )
        return await self._with_fallback(
            lambda: self._structured(BudgetBreakdown, prompt, ctx),
            lambda: mock_llm.optimize_budget(req, flights, hotels, places, restaurants),
            "budget_optimizer",
        )


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
        top_flights = [f.model_dump(exclude_none=True) for f in flights[:2]]
        top_hotels = [h.model_dump(exclude_none=True) for h in hotels[:2]]
        top_places = [{"name": p.name, "category": p.category, "rating": p.rating} for p in places[:5]]
        top_restaurants = [{"name": r.name, "cuisine": r.cuisine, "rating": r.rating} for r in restaurants[:5]]
        ctx = (
            f"Requirements: {req.model_dump_json(exclude_none=True)}\nDestination: {destination}\n"
            f"Flights: {top_flights}\nHotels: {top_hotels}\n"
            f"Places: {top_places}\nRestaurants: {top_restaurants}\n"
            f"Transportation: {transportation.model_dump_json(exclude_none=True) if transportation else '{}'}\n"
            f"Weather: {weather.model_dump_json(exclude_none=True)}\nBudget: {budget.model_dump_json(exclude_none=True)}"
        )
        return await self._with_fallback(
            lambda: self._structured(ItineraryModel, prompt, ctx),
            lambda: mock_llm.generate_itinerary(req, destination, flights, hotels, places, restaurants, weather, budget, transportation),
            "itinerary_generator",
        )


    # -- 7. Critic --------------------------------------------------------------
    async def critic_review(
        self, req: TripRequirements, itinerary: ItineraryModel, budget: BudgetBreakdown, places: list[PlaceModel],
    ) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.critic_review(req, itinerary, budget, places))
        prompt = load_prompt("critic")
        ctx = (
            f"Requirements: {req.model_dump_json(exclude_none=True)}\nItinerary: {itinerary.model_dump_json(exclude_none=True)}\n"
            f"Budget: {budget.model_dump_json(exclude_none=True)}"
        )
        return await self._with_fallback(
            lambda: self._structured(CriticResult, prompt, ctx),
            lambda: mock_llm.critic_review(req, itinerary, budget, places),
            "critic",
        )


    # -- 8. Conversational modification -----------------------------------------
    async def interpret_modification(self, message: str, req: TripRequirements) -> LLMResult:
        if self.settings.use_mock_llm:
            return self._mock_result(mock_llm.interpret_modification(message, req))
        prompt = load_prompt("modification_interpreter")
        ctx = f"Current requirements: {req.model_dump_json(exclude_none=True)}\nUser message: {message}"
        return await self._with_fallback(
            lambda: self._structured(ModificationInterpretation, prompt, ctx, cheap=True),
            lambda: mock_llm.interpret_modification(message, req),
            "modification_interpreter",
        )

