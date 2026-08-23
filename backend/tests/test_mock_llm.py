"""
Tests for app/ai/mock_llm.py -- the deterministic fallback reasoning layer
that lets the whole graph run with zero LLM API keys (DEMO_MODE).
"""
from __future__ import annotations

from app.ai import mock_llm as m
from app.schemas.domain import (
    BudgetBreakdown, CriticResult, FlightOptionModel, HotelOptionModel,
    ItineraryActivityModel, ItineraryDayModel, ItineraryModel, PlaceModel,
    TripRequirements, WeatherOutlook,
)

CANONICAL_PROMPT = (
    "I want to visit Japan for 8 days in October. My budget is \u20b91,50,000. "
    "I like nature, anime, food and photography. I don't like crowded tourist "
    "attractions. I am traveling with one friend. I prefer comfortable hotels "
    "and don't want extremely long travel days."
)


class TestExtractRequirements:
    def test_canonical_example_extracts_correctly(self):
        req = m.extract_requirements(CANONICAL_PROMPT)
        assert req.destination == "Japan"
        assert req.duration_days == 8
        assert req.budget_amount == 150000.0
        assert req.budget_currency == "INR"
        assert req.travelers == 2
        assert "nature" in req.activity_preferences
        assert "anime" in req.activity_preferences
        assert "food" in req.food_preferences
        assert "crowded tourist attractions" in req.dislikes
        assert req.pace == "relaxed"
        assert req.origin is None  # deliberately omitted in the canonical prompt

    def test_dislike_detection_tolerates_missing_apostrophe(self):
        req = m.extract_requirements("I dont like long queues.")
        assert "long queues" in req.dislikes

    def test_bare_reply_resolves_single_missing_field(self):
        base = m.extract_requirements(CANONICAL_PROMPT)
        assert base.origin is None
        resumed = m.extract_requirements("Mumbai", base=base, expected_fields=["origin"])
        assert resumed.origin == "Mumbai"
        # Everything else from the first turn must survive the merge.
        assert resumed.destination == "Japan"
        assert resumed.budget_amount == 150000.0

    def test_bare_reply_does_not_overwrite_already_known_field(self):
        base = TripRequirements(origin="Delhi", destination="Japan")
        resumed = m.extract_requirements("Delhi", base=base, expected_fields=["origin"])
        assert resumed.origin == "Delhi"


class TestMissingInfoChecker:
    def test_flags_origin_as_blocking(self):
        req = m.extract_requirements(CANONICAL_PROMPT)
        result = m.check_missing_info(req)
        assert result.can_proceed is False
        assert "origin" in result.missing_fields

    def test_proceeds_once_all_critical_fields_present(self):
        req = m.extract_requirements(CANONICAL_PROMPT)
        req.origin = "Mumbai"
        result = m.check_missing_info(req)
        assert result.can_proceed is True
        assert result.missing_fields == []


class TestRanking:
    def test_rank_places_excludes_high_crowd_when_disliked(self):
        req = TripRequirements(dislikes=["crowded tourist attractions"], activity_preferences=["nature"])
        options = [
            PlaceModel(name="Quiet Garden", category="nature", crowd_level="low", rating=4.0),
            PlaceModel(name="Packed Shrine", category="nature", crowd_level="high", rating=4.9),
        ]
        ranked = m.rank_places(req, options)
        assert "Packed Shrine" not in [p.name for p in ranked]

    def test_rank_places_relaxes_filter_on_retry(self):
        req = TripRequirements(dislikes=["crowded tourist attractions"], activity_preferences=["nature"])
        options = [
            PlaceModel(name="Quiet Garden", category="nature", crowd_level="low", rating=4.0),
            PlaceModel(name="Packed Shrine", category="nature", crowd_level="high", rating=4.9),
        ]
        ranked = m.rank_places(req, options, relax_crowd_filter=True)
        assert "Packed Shrine" in [p.name for p in ranked]
        # Still deprioritized even when included.
        assert ranked[-1].name == "Packed Shrine"

    def test_rank_flights_prioritizes_cost_on_retry(self):
        req = TripRequirements(pace="relaxed")
        options = [
            FlightOptionModel(provider="mock", origin="A", destination="B", depart_at="x", price=5000, stops=1),
            FlightOptionModel(provider="mock", origin="A", destination="B", depart_at="x", price=3000, stops=2),
        ]
        ranked = m.rank_flights(req, options, prioritize_cost=True)
        assert ranked[0].price == 3000


class TestBudgetOptimizer:
    def test_applies_optimizations_when_over_budget(self):
        req = TripRequirements(budget_amount=10000, budget_currency="INR", duration_days=3, travelers=1)
        flights = [FlightOptionModel(provider="mock", origin="A", destination="B", depart_at="x", price=3000)]
        hotels = [HotelOptionModel(provider="mock", name="Hotel", price_per_night=5000)]
        budget = m.optimize_budget(req, flights, hotels, [], [])
        assert budget.total_estimated <= sum(
            l.estimated_amount for l in budget.lines
        )  # internal consistency
        if budget.over_budget:
            assert len(budget.optimizations_applied) > 0

    def test_under_budget_stays_untouched(self):
        req = TripRequirements(budget_amount=10_000_000, budget_currency="INR", duration_days=2, travelers=1)
        flights = [FlightOptionModel(provider="mock", origin="A", destination="B", depart_at="x", price=1000)]
        hotels = [HotelOptionModel(provider="mock", name="Hotel", price_per_night=1000)]
        budget = m.optimize_budget(req, flights, hotels, [], [])
        assert budget.over_budget is False
        assert budget.optimizations_applied == []


class TestCriticReview:
    def _base_itinerary(self, n_days: int, attractions_per_day: int) -> ItineraryModel:
        days = []
        for d in range(1, n_days + 1):
            activities = [
                ItineraryActivityModel(activity_type="attraction", title=f"Day{d}-Attraction{i}")
                for i in range(attractions_per_day)
            ]
            days.append(ItineraryDayModel(day_number=d, title=f"Day {d}", activities=activities))
        return ItineraryModel(days=days, total_estimated_cost=1000, currency="INR")

    def test_approves_clean_itinerary(self):
        req = TripRequirements(duration_days=3)
        itinerary = self._base_itinerary(3, 1)
        budget = BudgetBreakdown(lines=[], total_estimated=1000, currency="INR", over_budget=False)
        result = m.critic_review(req, itinerary, budget, [])
        assert result.approved is True
        assert result.issues == []

    def test_flags_over_budget_and_recommends_correct_nodes(self):
        req = TripRequirements(duration_days=3)
        itinerary = self._base_itinerary(3, 1)
        budget = BudgetBreakdown(lines=[], total_estimated=999999, currency="INR", over_budget=True, over_budget_by=5000)
        result = m.critic_review(req, itinerary, budget, [])
        assert result.approved is False
        assert any(i.category == "budget" for i in result.issues)
        assert "flight_research" in result.recommended_searches
        assert "hotel_research" in result.recommended_searches

    def test_flags_underutilized_middle_day(self):
        req = TripRequirements(duration_days=4)
        days = [
            ItineraryDayModel(day_number=1, title="Day 1", activities=[]),
            ItineraryDayModel(day_number=2, title="Day 2", activities=[]),  # no attractions -- should flag
            ItineraryDayModel(day_number=3, title="Day 3", activities=[
                ItineraryActivityModel(activity_type="attraction", title="Something")
            ]),
            ItineraryDayModel(day_number=4, title="Day 4", activities=[]),  # last day -- exempt
        ]
        itinerary = ItineraryModel(days=days, total_estimated_cost=0, currency="INR")
        budget = BudgetBreakdown(lines=[], total_estimated=0, currency="INR", over_budget=False)
        result = m.critic_review(req, itinerary, budget, [])
        assert result.approved is False
        descriptions = " ".join(i.description for i in result.issues)
        assert "Day 2" in descriptions
        assert "Day 4" not in descriptions  # last day is exempt

    def test_flags_duplicate_attractions(self):
        req = TripRequirements(duration_days=2)
        days = [
            ItineraryDayModel(day_number=1, title="Day 1", activities=[
                ItineraryActivityModel(activity_type="attraction", title="Same Place")
            ]),
            ItineraryDayModel(day_number=2, title="Day 2", activities=[
                ItineraryActivityModel(activity_type="attraction", title="Same Place")
            ]),
        ]
        itinerary = ItineraryModel(days=days, total_estimated_cost=0, currency="INR")
        budget = BudgetBreakdown(lines=[], total_estimated=0, currency="INR", over_budget=False)
        result = m.critic_review(req, itinerary, budget, [])
        assert any(i.category == "logistics" for i in result.issues)


class TestInterpretModification:
    def test_hotels_too_expensive(self):
        req = TripRequirements()
        result = m.interpret_modification("Hotels are too expensive.", req)
        assert "hotel_research" in result.nodes_to_rerun
        assert "budget_friendly" in "".join(result.changed_fields.get("hotel_preferences", [])).replace("-", "_") or \
            "budget-friendly" in result.changed_fields.get("hotel_preferences", [])

    def test_remove_museums(self):
        req = TripRequirements()
        result = m.interpret_modification("Please remove museums, I've seen enough.", req)
        assert "museums" in result.changed_fields.get("avoid", [])
        assert "places_research" in result.nodes_to_rerun

    def test_change_destination(self):
        req = TripRequirements(destination="Tokyo")
        result = m.interpret_modification("Change Tokyo to Kyoto", req)
        assert result.changed_fields.get("destination") == "Kyoto"

    def test_increase_budget(self):
        req = TripRequirements(budget_amount=150000)
        result = m.interpret_modification("I can spend another 20000", req)
        assert result.changed_fields.get("budget_amount") == 170000.0
        assert "budget_optimizer" in result.nodes_to_rerun
