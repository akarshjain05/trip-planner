"""
Deterministic, rule-based stand-ins for every LLM-backed node.

These are used automatically when DEMO_MODE=true or no provider API key is
configured (see Settings.use_mock_llm) so the entire LangGraph workflow --
including the critic/replanning loop -- can run and be unit-tested with zero
paid API calls. This is a genuine, documented fallback (not a disguised
LLM call): every value returned here is computed from simple, inspectable
rules, and callers are expected to label results accordingly (the
`is_mock` / `used_mock_llm` flags threaded through state and DB rows).

When a real provider key IS configured and DEMO_MODE=false, none of this
module is used -- app/ai/orchestrator.py calls the real LLM instead.
"""
from __future__ import annotations

import calendar
import datetime as dt
import re

from app.schemas.domain import (
    BudgetBreakdown,
    BudgetLine,
    CriticIssue,
    CriticResult,
    DestinationCandidate,
    DestinationResearchResult,
    FlightOptionModel,
    HotelOptionModel,
    ItineraryActivityModel,
    ItineraryDayModel,
    ItineraryModel,
    MissingInfoResult,
    ModificationInterpretation,
    PlaceModel,
    RestaurantModel,
    TransportationPlan,
    TransportLeg,
    TripRequirements,
    DailyWeather,
    WeatherOutlook,
)

_WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1,
}
_MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
_FOOD_WORDS = {"food", "cuisine", "street food", "local food", "dining"}


# ---------------------------------------------------------------------------
# 1. Requirement extraction
# ---------------------------------------------------------------------------
def extract_requirements(
    text: str, base: TripRequirements | None = None, expected_fields: list[str] | None = None
) -> TripRequirements:
    """Best-effort regex/keyword extraction. This is intentionally simple --
    it exists so the graph is runnable offline, not as a substitute for real
    NLU. With a real LLM_PROVIDER configured, the orchestrator uses the
    actual model instead of this function.

    `expected_fields` (from the prior MissingInfoResult) disambiguates short
    bare replies to a clarifying question, e.g. answering just "Mumbai" to
    "what's your origin?" -- without that context a bare place name has no
    reliable pattern to anchor on.
    """
    req = base.model_copy(deep=True) if base else TripRequirements()
    t = text.strip()
    low = t.lower()
    is_short_bare_reply = len(t.split()) <= 5 and not re.search(r"[.!?]", t)

    # --- destination ---
    m = re.search(r"\b(?:visit|trip to|travel to|go to|going to)\s+([A-Z][A-Za-z\s]{1,40}?)(?:\s+for\b|\s+in\b|[.,]|$)", t)
    if m:
        req.destination = m.group(1).strip()

    # --- origin ---
    m = re.search(r"\bfrom\s+([A-Z][A-Za-z\s]{1,40}?)(?:\s+to\b|[.,]|$)", t)
    if m:
        req.origin = m.group(1).strip()

    # --- duration ---
    m = re.search(r"(\d+)\s*[- ]?\s*day", low)
    if m:
        req.duration_days = int(m.group(1))

    # --- month -> approximate dates ---
    for name, idx in _MONTHS.items():
        if re.search(rf"\b{name}\b", low):
            today = dt.date.today()
            year = today.year if idx >= today.month else today.year + 1
            start = dt.date(year, idx, 1)
            req.start_date = req.start_date or start
            if req.duration_days:
                req.end_date = start + dt.timedelta(days=req.duration_days - 1)
            break

    # --- budget ---
    m = re.search(r"[₹$€£]\s?([\d,]+)", t) or re.search(r"budget\D{0,10}([\d,]{4,})", low)
    if m:
        amount_str = m.group(1).replace(",", "")
        if amount_str.isdigit():
            req.budget_amount = float(amount_str)
    if "₹" in t or re.search(r"\brs\.?\b|\binr\b|\brupee", low):
        req.budget_currency = "INR"
    elif "$" in t or "usd" in low:
        req.budget_currency = "USD"
    elif "€" in t or "eur" in low:
        req.budget_currency = "EUR"
    elif "£" in t or "gbp" in low:
        req.budget_currency = "GBP"

    # --- travelers ---
    m = re.search(r"with\s+(\w+)\s+friend", low) or re.search(r"with\s+(\w+)\s+other", low)
    if m:
        n = _WORD_NUMBERS.get(m.group(1))
        if n is None and m.group(1).isdigit():
            n = int(m.group(1))
        if n:
            req.travelers = n + 1
            req.adults = n + 1
    m2 = re.search(r"(\d+)\s+travelers?", low)
    if m2:
        req.travelers = int(m2.group(1))
        req.adults = req.travelers

    # --- likes -> activity/food preferences ---
    m = re.search(r"\bi like\s+([^.]+)\.", t, re.IGNORECASE)
    if m:
        items = [i.strip(" .") for i in re.split(r",| and ", m.group(1)) if i.strip(" .")]
        for item in items:
            bucket = req.food_preferences if item.lower() in _FOOD_WORDS else req.activity_preferences
            if item not in bucket:
                bucket.append(item)

    # --- dislikes ---
    for pattern in [
        r"i\s*don'?t\s+like\s+([^.]+)\.",
        r"i\s+do\s*not\s+like\s+([^.]+)\.",
        r"i\s+dislike\s+([^.]+)\.",
        r"\bavoid\s+([^.]+)\.",
    ]:
        m = re.search(pattern, t, re.IGNORECASE)
        if m:
            item = m.group(1).strip(" .")
            if item and item not in req.dislikes:
                req.dislikes.append(item)

    # --- hotel preferences ---
    m = re.search(r"prefer\s+([a-z\s]+?)\s+hotels?", low)
    if m:
        pref = m.group(1).strip()
        if pref and pref not in req.hotel_preferences:
            req.hotel_preferences.append(pref)

    # --- pace ---
    if "extremely long travel days" in low or "no long travel days" in low or "relaxed" in low:
        req.pace = req.pace or "relaxed"
    elif "packed" in low or "jam-packed" in low:
        req.pace = req.pace or "packed"
    else:
        req.pace = req.pace or "moderate"

    # --- bare short reply to a single-field clarifying question ---
    # e.g. expected_fields == ["origin"] and the user just typed "Mumbai".
    if expected_fields and len(expected_fields) == 1 and is_short_bare_reply:
        field = expected_fields[0]
        if field == "origin" and not req.origin:
            req.origin = t.title()
        elif field == "destination" and not req.destination:
            req.destination = t.title()

    return req


def check_missing_info(req: TripRequirements) -> MissingInfoResult:
    missing = []
    if not req.origin:
        missing.append("origin")
    if not req.destination:
        missing.append("destination")
    if not req.duration_days and not (req.start_date and req.end_date):
        missing.append("trip duration or dates")

    if not missing:
        return MissingInfoResult(missing_fields=[], clarifying_question=None, can_proceed=True)

    question = "Could you share your " + ", ".join(missing) + " so I can start planning?"
    return MissingInfoResult(missing_fields=missing, clarifying_question=question, can_proceed=False)


# ---------------------------------------------------------------------------
# 2. Destination research
# ---------------------------------------------------------------------------
_DESTINATION_LIBRARY = [
    {"name": "Kyoto, Japan", "tags": {"nature", "anime", "photography", "culture", "food"}},
    {"name": "Queenstown, New Zealand", "tags": {"nature", "adventure", "photography"}},
    {"name": "Lisbon, Portugal", "tags": {"food", "culture", "photography", "nightlife"}},
    {"name": "Bali, Indonesia", "tags": {"nature", "beach", "food", "relaxation"}},
]


def research_destinations(req: TripRequirements) -> DestinationResearchResult:
    if req.destination:
        chosen = DestinationCandidate(
            name=req.destination,
            country=None,
            rank=1,
            reasons="User-specified destination; matches stated preferences based on available demo data.",
            suitability_score=0.85,
        )
        return DestinationResearchResult(candidates=[chosen], chosen=chosen.name)

    prefs = {p.lower() for p in req.activity_preferences}
    scored = []
    for entry in _DESTINATION_LIBRARY:
        overlap = len(prefs & entry["tags"])
        scored.append((overlap, entry["name"]))
    scored.sort(reverse=True)
    candidates = [
        DestinationCandidate(
            name=name, rank=i + 1,
            reasons=f"Matches {overlap} of your stated interests (demo scoring).",
            suitability_score=min(0.5 + 0.15 * overlap, 0.95),
        )
        for i, (overlap, name) in enumerate(scored[:3])
    ]
    return DestinationResearchResult(candidates=candidates, chosen=candidates[0].name)


# ---------------------------------------------------------------------------
# 3. Ranking already-fetched provider results
# ---------------------------------------------------------------------------
def rank_flights(req: TripRequirements, options: list[FlightOptionModel], prioritize_cost: bool = False) -> list[FlightOptionModel]:
    if prioritize_cost:
        # Retry after a critic budget rejection: cost now trumps the
        # stop-count comfort preference (spec's own optimization ladder
        # explicitly includes "try alternative flight dates/cabin").
        ranked = sorted(options, key=lambda f: f.price)
    else:
        prefers_direct = (req.pace == "relaxed") or any("long" in d.lower() for d in req.dislikes)
        ranked = sorted(options, key=lambda f: (f.stops if prefers_direct else 0, f.price))
    return ranked[:3]


def rank_hotels(req: TripRequirements, options: list[HotelOptionModel]) -> list[HotelOptionModel]:
    budget_hint = (req.budget_amount or 0) / max(req.duration_days or 1, 1) * 0.35
    def score(h: HotelOptionModel) -> tuple:
        over_hint = 1 if budget_hint and h.price_per_night > budget_hint else 0
        return (over_hint, -(h.rating or 0))
    return sorted(options, key=score)[:3]


def rank_places(req: TripRequirements, options: list[PlaceModel], relax_crowd_filter: bool = False) -> list[PlaceModel]:
    dislikes_crowds = any("crowd" in d.lower() for d in req.dislikes + req.avoid)
    if dislikes_crowds and not relax_crowd_filter:
        pool = [p for p in options if p.crowd_level != "high"]
        pool = pool or options
    else:
        # Retry after a critic rejection (e.g. "underutilized day"): widen the
        # search instead of repeating the exact same filtered result -- keep
        # every option but still deprioritize high-crowd ones in the sort.
        pool = list(options)
    prefs = {p.lower() for p in req.activity_preferences}

    def score(p: PlaceModel) -> tuple:
        match = 1 if p.category and p.category.lower() in prefs else 0
        crowd_penalty = 1 if (dislikes_crowds and p.crowd_level == "high") else 0
        return (-match, crowd_penalty, -(p.rating or 0))
    return sorted(pool, key=score)


def rank_restaurants(req: TripRequirements, options: list[RestaurantModel]) -> list[RestaurantModel]:
    prefs = {p.lower() for p in req.food_preferences}
    def score(r: RestaurantModel) -> tuple:
        match = 1 if r.cuisine and r.cuisine.lower() in prefs else 0
        return (-match, -(r.rating or 0))
    return sorted(options, key=score)


# ---------------------------------------------------------------------------
# 4. Transportation / weather
# ---------------------------------------------------------------------------
def plan_transportation(req: TripRequirements, hotel: HotelOptionModel | None) -> TransportationPlan:
    prefers = req.transportation_preferences
    mode = prefers[0] if prefers else "metro/train"
    legs = [
        TransportLeg(mode="taxi", from_location="Airport", to_location=hotel.name if hotel else "Hotel",
                     estimated_minutes=45, estimated_cost=25.0),
    ]
    return TransportationPlan(
        airport_transfer="Pre-booked taxi or airport express train recommended on arrival.",
        intercity=[f"Use {mode} for most inter-attraction travel; it's typically the fastest and cheapest option."],
        local_recommendation=f"A rechargeable local transit card covers {mode} for the whole trip.",
        legs=legs,
    )


def weather_outlook(req: TripRequirements) -> WeatherOutlook:
    days = req.duration_days or 1
    start = req.start_date
    conditions = ["Sunny", "Partly cloudy", "Sunny", "Light rain", "Partly cloudy", "Sunny", "Overcast", "Sunny"]
    out = []
    for i in range(days):
        out.append(DailyWeather(
            date=(start + dt.timedelta(days=i)) if start else None,
            day_number=i + 1,
            condition=conditions[i % len(conditions)],
            temp_high_c=24.0 + (i % 3),
            temp_low_c=15.0 + (i % 3),
            rain_chance_pct=60 if conditions[i % len(conditions)] == "Light rain" else 10,
        ))
    return WeatherOutlook(
        days=out,
        seasonal_note="Demo weather data (not a live forecast) -- configure WEATHER_PROVIDER for real forecasts.",
    )


# ---------------------------------------------------------------------------
# 5. Budget optimization
# ---------------------------------------------------------------------------
def optimize_budget(
    req: TripRequirements,
    flights: list[FlightOptionModel],
    hotels: list[HotelOptionModel],
    places: list[PlaceModel],
    restaurants: list[RestaurantModel],
) -> BudgetBreakdown:
    currency = req.budget_currency
    days = req.duration_days or 1
    travelers = max(req.travelers, 1)

    flight_cost = (flights[0].price if flights else 0) * travelers
    hotel_cost = (hotels[0].price_per_night if hotels else 0) * days
    activities_cost = sum((p.estimated_cost or 0) for p in places[: min(len(places), days * 2)]) * travelers
    food_cost = 1200 * days * travelers  # demo per-day food estimate
    local_transport = 400 * days
    intercity_transport = 0.0
    shopping = 0.10 * (req.budget_amount or (flight_cost + hotel_cost + activities_cost))
    buffer = 0.08 * (flight_cost + hotel_cost + activities_cost + food_cost)
    taxes = 0.05 * (flight_cost + hotel_cost)

    lines = [
        BudgetLine(category="flights", estimated_amount=round(flight_cost, 2), currency=currency),
        BudgetLine(category="hotels", estimated_amount=round(hotel_cost, 2), currency=currency),
        BudgetLine(category="local_transport", estimated_amount=round(local_transport, 2), currency=currency),
        BudgetLine(category="intercity_transport", estimated_amount=round(intercity_transport, 2), currency=currency),
        BudgetLine(category="food", estimated_amount=round(food_cost, 2), currency=currency),
        BudgetLine(category="activities", estimated_amount=round(activities_cost, 2), currency=currency),
        BudgetLine(category="shopping_allowance", estimated_amount=round(shopping, 2), currency=currency),
        BudgetLine(category="emergency_buffer", estimated_amount=round(buffer, 2), currency=currency),
        BudgetLine(category="taxes_fees", estimated_amount=round(taxes, 2), currency=currency),
    ]
    total = round(sum(l.estimated_amount for l in lines), 2)
    optimizations: list[str] = []

    if req.budget_amount and total > req.budget_amount:
        # Optimization ladder: trim hotel first, then activities, then shopping/buffer.
        over_by = total - req.budget_amount
        hotel_line = next(l for l in lines if l.category == "hotels")
        cut = min(hotel_line.estimated_amount * 0.20, over_by)
        if cut > 0:
            hotel_line.estimated_amount = round(hotel_line.estimated_amount - cut, 2)
            optimizations.append(f"Reduced hotel budget by {cut:.0f} {currency} (moved to a lower hotel tier).")
            over_by -= cut

        if over_by > 0:
            act_line = next(l for l in lines if l.category == "activities")
            cut2 = min(act_line.estimated_amount * 0.25, over_by)
            if cut2 > 0:
                act_line.estimated_amount = round(act_line.estimated_amount - cut2, 2)
                optimizations.append(f"Trimmed {cut2:.0f} {currency} from activities (dropped lowest-priority items).")
                over_by -= cut2

        if over_by > 0:
            shop_line = next(l for l in lines if l.category == "shopping_allowance")
            cut3 = min(shop_line.estimated_amount, over_by)
            shop_line.estimated_amount = round(shop_line.estimated_amount - cut3, 2)
            optimizations.append(f"Reduced shopping allowance by {cut3:.0f} {currency}.")
            over_by -= cut3

        total = round(sum(l.estimated_amount for l in lines), 2)

    over_budget = bool(req.budget_amount and total > req.budget_amount)
    over_by_final = round(total - req.budget_amount, 2) if (req.budget_amount and over_budget) else 0.0

    return BudgetBreakdown(
        lines=lines, total_estimated=total, currency=currency,
        over_budget=over_budget, over_budget_by=max(over_by_final, 0.0),
        optimizations_applied=optimizations,
    )


# ---------------------------------------------------------------------------
# 6. Itinerary generation
# ---------------------------------------------------------------------------
def generate_itinerary(
    req: TripRequirements,
    destination: str,
    flights: list[FlightOptionModel],
    hotels: list[HotelOptionModel],
    places: list[PlaceModel],
    restaurants: list[RestaurantModel],
    weather: WeatherOutlook,
    budget: BudgetBreakdown,
    transportation: "TransportationPlan | None" = None,
) -> ItineraryModel:
    days = req.duration_days or 1
    hotel = hotels[0] if hotels else None
    days_out: list[ItineraryDayModel] = []
    place_idx = 0
    transfer_leg = transportation.legs[0] if (transportation and transportation.legs) else None

    for d in range(1, days + 1):
        activities: list[ItineraryActivityModel] = []
        weather_day = next((w for w in weather.days if w.day_number == d), None)

        if d == 1 and flights:
            activities.append(ItineraryActivityModel(
                time="09:30", activity_type="flight", title=f"Arrival flight ({flights[0].airline or flights[0].provider})",
                description=f"{flights[0].origin} -> {flights[0].destination}", estimated_cost=flights[0].price,
                duration_minutes=flights[0].duration_minutes,
            ))
            transfer_minutes = transfer_leg.estimated_minutes if transfer_leg else 45
            transfer_cost = transfer_leg.estimated_cost if transfer_leg else 25.0
            transfer_note = transportation.airport_transfer if transportation else None
            activities.append(ItineraryActivityModel(
                time="11:00", activity_type="transfer", title="Hotel transfer",
                description=transfer_note or f"Transfer to {hotel.name if hotel else 'hotel'}",
                estimated_cost=transfer_cost, duration_minutes=transfer_minutes,
            ))
            if hotel:
                activities.append(ItineraryActivityModel(
                    time="12:00", activity_type="hotel_checkin", title=f"Check in: {hotel.name}",
                    location=hotel.location, estimated_cost=0,
                ))

        # Two attractions + one meal per mid-trip day, lighter on arrival/departure days.
        max_places_today = 1 if d in (1, days) else 2
        for _ in range(max_places_today):
            if place_idx < len(places):
                p = places[place_idx]
                place_idx += 1
                activities.append(ItineraryActivityModel(
                    time="14:00" if len(activities) < 4 else "17:00",
                    activity_type="attraction", title=p.name, description=p.description,
                    location=p.name, estimated_cost=p.estimated_cost,
                    duration_minutes=p.estimated_visit_minutes, source_ref=None,
                ))

        if restaurants:
            r = restaurants[(d - 1) % len(restaurants)]
            activities.append(ItineraryActivityModel(
                time="19:30", activity_type="meal", title=f"Dinner: {r.name}",
                description=r.description, estimated_cost=None,
            ))

        if d == days and flights:
            activities.append(ItineraryActivityModel(
                time="20:00", activity_type="hotel_checkout", title="Hotel checkout",
            ))
            activities.append(ItineraryActivityModel(
                time="22:00", activity_type="flight", title="Return flight", estimated_cost=0,
            ))

        days_out.append(ItineraryDayModel(
            day_number=d,
            date=weather_day.date if weather_day else None,
            title=f"Day {d} — {'Arrival' if d == 1 else ('Departure' if d == days else destination)}",
            weather_summary=f"{weather_day.condition}, {weather_day.temp_high_c:.0f}°C" if weather_day else None,
            activities=activities,
        ))

    return ItineraryModel(days=days_out, total_estimated_cost=budget.total_estimated, currency=budget.currency)


# ---------------------------------------------------------------------------
# 7. Critic
# ---------------------------------------------------------------------------
_KNOWN_NODES = [
    "destination_research", "flight_research", "hotel_research", "places_research",
    "food_research", "transportation", "weather_season", "budget_optimizer", "itinerary_generator",
]


def critic_review(req: TripRequirements, itinerary: ItineraryModel, budget: BudgetBreakdown, places: list[PlaceModel]) -> CriticResult:
    issues: list[CriticIssue] = []
    recommended: list[str] = []

    if budget.over_budget:
        issues.append(CriticIssue(
            category="budget", severity="high",
            description=f"Itinerary is over budget by {budget.over_budget_by:.0f} {budget.currency} even after optimization.",
            suggested_fix="Select a lower hotel tier, a cheaper flight, or remove a paid activity.",
        ))
        recommended += ["flight_research", "hotel_research", "budget_optimizer", "itinerary_generator"]

    dislikes_crowds = any("crowd" in d.lower() for d in req.dislikes + req.avoid)
    if dislikes_crowds and any(p.crowd_level == "high" for p in places):
        crowded_used = [p.name for p in places if p.crowd_level == "high"]
        if any(a.title in crowded_used for day in itinerary.days for a in day.activities):
            issues.append(CriticIssue(
                category="preference", severity="medium",
                description="Itinerary includes a high-crowd attraction despite the traveler disliking crowds.",
                suggested_fix="Swap for a lower-crowd alternative.",
            ))
            recommended += ["places_research", "itinerary_generator"]

    for day in itinerary.days:
        non_transfer = [a for a in day.activities if a.activity_type not in ("transfer", "hotel_checkin", "hotel_checkout")]
        if req.pace == "relaxed" and len(non_transfer) > 4:
            issues.append(CriticIssue(
                category="schedule", severity="medium",
                description=f"Day {day.day_number} has {len(non_transfer)} activities, which is packed for a relaxed pace.",
                suggested_fix="Move one activity to a lighter day or drop it.",
            ))
            if "itinerary_generator" not in recommended:
                recommended.append("itinerary_generator")

        attraction_count = sum(1 for a in day.activities if a.activity_type == "attraction")
        is_edge_day = day.day_number in (1, len(itinerary.days))
        if attraction_count == 0 and not is_edge_day:
            issues.append(CriticIssue(
                category="schedule", severity="medium",
                description=f"Day {day.day_number} has no planned attraction -- underutilized.",
                suggested_fix="Source more candidate places so every day has something planned.",
            ))
            for n in ("places_research", "itinerary_generator"):
                if n not in recommended:
                    recommended.append(n)

    all_titles = [a.title for day in itinerary.days for a in day.activities if a.activity_type == "attraction"]
    if len(all_titles) != len(set(all_titles)):
        issues.append(CriticIssue(
            category="logistics", severity="medium",
            description="The same attraction is scheduled more than once across the itinerary.",
            suggested_fix="De-duplicate attractions across days.",
        ))
        for n in ("places_research", "itinerary_generator"):
            if n not in recommended:
                recommended.append(n)

    severity = "none"
    if issues:
        severity = max((i.severity for i in issues), key=lambda s: {"low": 0, "medium": 1, "high": 2}[s])

    recommended = [n for n in dict.fromkeys(recommended) if n in _KNOWN_NODES]
    return CriticResult(
        approved=not issues,
        issues=issues,
        severity=severity,
        required_changes=[i.suggested_fix for i in issues if i.suggested_fix],
        recommended_searches=recommended,
    )


# ---------------------------------------------------------------------------
# 8. Conversational modification
# ---------------------------------------------------------------------------
def interpret_modification(message: str, req: TripRequirements) -> ModificationInterpretation:
    low = message.lower()
    changed: dict = {}
    nodes: list[str] = []

    if ("expensive" in low or "cheaper" in low) and "hotel" in low:
        changed["hotel_preferences"] = list(set(req.hotel_preferences + ["budget-friendly"]))
        nodes += ["hotel_research", "budget_optimizer", "itinerary_generator"]

    elif "museum" in low and ("remove" in low or "no more" in low or "drop" in low):
        changed["avoid"] = list(set(req.avoid + ["museums"]))
        nodes += ["places_research", "itinerary_generator"]

    elif "nightlife" in low:
        changed["activity_preferences"] = list(set(req.activity_preferences + ["nightlife"]))
        nodes += ["places_research", "itinerary_generator"]

    elif "spend another" in low or ("increase" in low and "budget" in low):
        m = re.search(r"[₹$€£]?\s?([\d,]+)", message)
        if m and req.budget_amount:
            extra = float(m.group(1).replace(",", ""))
            changed["budget_amount"] = req.budget_amount + extra
        nodes += ["budget_optimizer", "itinerary_generator"]

    else:
        m = re.search(r"change\s+([a-z\s]+?)\s+to\s+([a-z\s]+)", low)
        if m:
            changed["destination"] = m.group(2).strip().title()
            nodes += _KNOWN_NODES + ["itinerary_generator"]
        elif "wake up" in low or "morning" in low or "start later" in low:
            changed["pace"] = "relaxed"
            nodes += ["itinerary_generator"]
        else:
            # Generic fallback: nothing specific recognized -- regenerate the
            # itinerary only, flagged for a human/real-LLM look if needed.
            nodes += ["itinerary_generator"]

    nodes = [n for n in dict.fromkeys(nodes) if n in _KNOWN_NODES or n == "itinerary_generator"]
    return ModificationInterpretation(
        summary=f"Interpreted (demo mode, rule-based): {message.strip()}",
        changed_fields=changed,
        nodes_to_rerun=nodes,
    )
