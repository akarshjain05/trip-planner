from __future__ import annotations

import datetime as dt

import pytest

from app.tools.cache import cached, make_cache_key
from app.tools.currency.mock import MockCurrencyProvider
from app.tools.flights.mock import MockFlightProvider
from app.tools.hotels.mock import MockHotelProvider
from app.tools.maps.mock import MockMapsProvider
from app.tools.places.mock import MockPlacesProvider
from app.tools.restaurants.mock import MockRestaurantProvider
from app.tools.weather.mock import MockWeatherProvider
from app.tools.web_search.mock import MockWebSearchProvider


class TestMockProviders:
    @pytest.mark.asyncio
    async def test_flights_are_labeled_mock_and_deterministic(self):
        p = MockFlightProvider()
        r1 = await p.search_flights("Mumbai", "Tokyo", dt.date(2026, 10, 1))
        r2 = await p.search_flights("Mumbai", "Tokyo", dt.date(2026, 10, 1))
        assert all(f.is_mock for f in r1)
        assert [f.price for f in r1] == [f.price for f in r2]  # same query -> same result

    @pytest.mark.asyncio
    async def test_hotels_return_a_price_tier_spread(self):
        p = MockHotelProvider()
        hotels = await p.search_hotels("Kyoto, Japan")
        prices = sorted(h.price_per_night for h in hotels)
        assert prices[0] < prices[-1]
        assert all(h.is_mock for h in hotels)

    @pytest.mark.asyncio
    async def test_places_curated_destination_has_crowd_variety(self):
        p = MockPlacesProvider()
        places = await p.search_places("Japan", ["nature", "anime"])
        levels = {pl.crowd_level for pl in places}
        assert "low" in levels or "medium" in levels
        assert "high" in levels

    @pytest.mark.asyncio
    async def test_places_generic_fallback_for_unknown_destination(self):
        p = MockPlacesProvider()
        places = await p.search_places("Nowhereland", ["hiking"])
        assert len(places) > 0
        assert all(pl.is_mock for pl in places)

    @pytest.mark.asyncio
    async def test_restaurants_returned(self):
        p = MockRestaurantProvider()
        restaurants = await p.search_restaurants("Japan", ["japanese"])
        assert len(restaurants) > 0

    @pytest.mark.asyncio
    async def test_weather_forecast_length_matches_days(self):
        p = MockWeatherProvider()
        forecast = await p.get_forecast("Japan", dt.date(2026, 10, 1), 5)
        assert len(forecast) == 5
        assert all(day["is_mock"] for day in forecast)

    @pytest.mark.asyncio
    async def test_currency_conversion_is_directionally_sane(self):
        p = MockCurrencyProvider()
        inr = await p.convert(1, "USD", "INR")
        usd = await p.convert(1, "INR", "USD")
        assert inr > 1  # 1 USD is worth much more than 1 INR
        assert usd < 1

    @pytest.mark.asyncio
    async def test_maps_travel_time_positive(self):
        p = MockMapsProvider()
        result = await p.estimate_travel_time("A", "B", "walking")
        assert result["duration_minutes"] > 0

    @pytest.mark.asyncio
    async def test_web_search_returns_labeled_demo_sources(self):
        p = MockWebSearchProvider()
        results = await p.search("best time to visit Kyoto")
        assert len(results) > 0
        assert all(r["source"] == "demo_web_search" for r in results)
        assert all("url" in r and "title" in r and "confidence" in r for r in results)


class TestCache:
    @pytest.mark.asyncio
    async def test_cache_hit_skips_refetch(self):
        calls = {"n": 0}

        async def fetch():
            calls["n"] += 1
            return {"v": 1}

        key = make_cache_key("test_cache", a=1)
        await cached(key, 5, fetch)
        await cached(key, 5, fetch)
        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_different_keys_both_fetch(self):
        calls = {"n": 0}

        async def fetch():
            calls["n"] += 1
            return {"v": calls["n"]}

        await cached(make_cache_key("test_cache", a=2), 5, fetch)
        await cached(make_cache_key("test_cache", a=3), 5, fetch)
        assert calls["n"] == 2
