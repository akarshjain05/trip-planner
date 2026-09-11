"""
Domain schemas shared between the LangGraph agent state and the API layer.

Every agent node that calls an LLM asks for one of these shapes via
structured output (see app/ai/providers.py). Keeping them here — instead of
scattered across node files — is what makes the contract between nodes
explicit: node N's output type is node N+1's input type.
"""
from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# 1. Requirement extraction
# ---------------------------------------------------------------------------
class TripRequirements(BaseModel):
    origin: str | None = Field(default=None, description="Departure city")
    origin_iata: str | None = Field(default=None, description="Departure airport 3-letter IATA code (e.g. LHR, CDG, JFK, BLR)")
    destination: str | None = Field(default=None, description="Destination city/country/region")
    destination_iata: str | None = Field(default=None, description="Destination airport 3-letter IATA code (e.g. DPS, HND)")
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    duration_days: int | None = None
    travelers: int = 1
    adults: int = 1
    children: int = 0
    budget_amount: float | None = None
    budget_currency: str = "INR"
    travel_style: str | None = Field(default=None, description="e.g. relaxed, adventurous, luxury, budget")
    hotel_preferences: list[str] = Field(default_factory=list)
    food_preferences: list[str] = Field(default_factory=list)
    activity_preferences: list[str] = Field(default_factory=list)
    dislikes: list[str] = Field(default_factory=list)
    must_see: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    pace: Literal["relaxed", "moderate", "packed"] | None = None
    accessibility_requirements: str | None = None
    transportation_preferences: list[str] = Field(default_factory=list)
    climate_preferences: str | None = None
    priorities: list[str] = Field(default_factory=list)

    @model_validator(mode='before')
    @classmethod
    def scrub_nulls(cls, data: dict) -> dict:
        if isinstance(data, dict):
            # Remove keys where value is explicitly None, letting pydantic use defaults
            return {k: v for k, v in data.items() if v is not None}
        return data


class MissingInfoResult(BaseModel):
    missing_fields: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None
    can_proceed: bool = True


# ---------------------------------------------------------------------------
# 2. Destination research
# ---------------------------------------------------------------------------
class DestinationCandidate(BaseModel):
    name: str
    country: str | None = None
    rank: int = 1
    reasons: str = ""
    suitability_score: float = Field(default=0.5, ge=0, le=1)


from pydantic import model_validator

class DestinationResearchResult(BaseModel):
    candidates: list[DestinationCandidate]
    chosen: str | None = Field(default=None, description="The destination chosen for the itinerary")

    @model_validator(mode='after')
    def default_chosen(self):
        if not self.chosen and self.candidates:
            self.chosen = self.candidates[0].name
        return self


# ---------------------------------------------------------------------------
# 3. Flights / Hotels / Places / Food
# ---------------------------------------------------------------------------
class FlightOptionModel(BaseModel):
    provider: str
    origin: str
    destination: str
    depart_at: str
    return_at: str | None = None
    airline: str | None = None
    price: float
    currency: str = "INR"
    duration_minutes: int | None = None
    stops: int = 0
    cabin: str = "economy"
    baggage: str | None = None
    is_mock: bool = True


class HotelOptionModel(BaseModel):
    provider: str
    name: str
    location: str | None = None
    price_per_night: float
    currency: str = "INR"
    rating: float | None = None
    distance_from_center_km: float | None = None
    amenities: list[str] = Field(default_factory=list)
    is_mock: bool = True


class PlaceModel(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    rating: float | None = None
    estimated_visit_minutes: int | None = None
    estimated_cost: float | None = None
    opening_hours: str | None = None
    crowd_level: Literal["low", "medium", "high"] | None = None
    is_mock: bool = True


class RestaurantModel(BaseModel):
    name: str
    cuisine: str | None = None
    price_level: Literal["$", "$$", "$$$", "$$$$"] | None = None
    description: str | None = None
    rating: float | None = None
    is_mock: bool = True


# ---------------------------------------------------------------------------
# 4. Transportation / Weather
# ---------------------------------------------------------------------------
class TransportLeg(BaseModel):
    mode: str  # walk | metro | train | taxi | rental_car | bus
    from_location: str
    to_location: str
    estimated_minutes: int
    estimated_cost: float | None = None


class TransportationPlan(BaseModel):
    airport_transfer: TransportLeg | str | None = None
    intercity: list[TransportLeg | str] = Field(default_factory=list)
    local_recommendation: str | None = None
    legs: list[TransportLeg] = Field(default_factory=list)


class DailyWeather(BaseModel):
    date: dt.date | None = None
    day_number: int
    condition: str
    temp_high_c: float | None = None
    temp_low_c: float | None = None
    rain_chance_pct: int | None = None
    note: str | None = None


class WeatherOutlook(BaseModel):
    days: list[DailyWeather] = Field(default_factory=list)
    seasonal_note: str | None = None


# ---------------------------------------------------------------------------
# 5. Budget
# ---------------------------------------------------------------------------
class BudgetLine(BaseModel):
    category: Literal[
        "flights", "hotels", "local_transport", "intercity_transport",
        "food", "activities", "shopping_allowance", "emergency_buffer", "taxes_fees",
    ]
    estimated_amount: float
    currency: str = "INR"


class BudgetBreakdown(BaseModel):
    lines: list[BudgetLine]
    total_estimated: float
    currency: str = "INR"
    over_budget: bool = False
    over_budget_by: float = 0.0
    optimizations_applied: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 6. Itinerary
# ---------------------------------------------------------------------------
class ItineraryActivityModel(BaseModel):
    time: str | None = None
    activity_type: Literal[
        "flight", "transfer", "meal", "attraction", "hotel_checkin",
        "hotel_checkout", "free_time", "other",
    ]
    title: str
    description: str | None = None
    location: str | None = None
    estimated_cost: float | None = None
    duration_minutes: int | None = None
    source_ref: str | None = None


class ItineraryDayModel(BaseModel):
    day_number: int
    date: dt.date | None = None
    title: str
    weather_summary: str | None = None
    activities: list[ItineraryActivityModel]


class ItineraryModel(BaseModel):
    days: list[ItineraryDayModel]
    total_estimated_cost: float
    currency: str = "INR"


# ---------------------------------------------------------------------------
# 7. Critic
# ---------------------------------------------------------------------------
class CriticIssue(BaseModel):
    category: str  # budget | schedule | preference | logistics | ...
    description: str
    severity: Literal["low", "medium", "high"]
    suggested_fix: str | None = None


class CriticResult(BaseModel):
    approved: bool
    issues: list[CriticIssue] = Field(default_factory=list)
    severity: Literal["none", "low", "medium", "high"] = "none"
    required_changes: list[str] = Field(default_factory=list)
    recommended_searches: list[str] = Field(
        default_factory=list,
        description=(
            "Node names to rerun, e.g. ['hotel_research', 'budget_optimizer']. "
            "Must be drawn from the known agent node names."
        ),
    )


# ---------------------------------------------------------------------------
# 8. Conversational modification
# ---------------------------------------------------------------------------
class ModificationInterpretation(BaseModel):
    summary: str
    changed_fields: dict = Field(default_factory=dict, description="Requirement fields to update")
    nodes_to_rerun: list[str] = Field(default_factory=list)
