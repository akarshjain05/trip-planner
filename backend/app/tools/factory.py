"""Single place that turns Settings.<X>_PROVIDER into a concrete adapter
instance. Agent nodes depend on this factory, never on a specific adapter
class -- that's what makes FLIGHTS_PROVIDER=amadeus a one-line .env change."""
from __future__ import annotations

from app.core.config import Settings
from app.tools.currency.mock import MockCurrencyProvider
from app.tools.flights.mock import MockFlightProvider
from app.tools.hotels.mock import MockHotelProvider
from app.tools.maps.mock import MockMapsProvider
from app.tools.places.mock import MockPlacesProvider
from app.tools.restaurants.mock import MockRestaurantProvider
from app.tools.weather.mock import MockWeatherProvider
from app.tools.web_search.mock import MockWebSearchProvider


def get_flight_provider(settings: Settings):
    if settings.FLIGHTS_PROVIDER == "amadeus" and not settings.DEMO_MODE:
        from app.tools.flights.amadeus import AmadeusFlightProvider
        return AmadeusFlightProvider(settings)
    return MockFlightProvider()


def get_hotel_provider(settings: Settings):
    if settings.HOTELS_PROVIDER == "booking" and not settings.DEMO_MODE:
        from app.tools.hotels.booking_stub import BookingComHotelProvider
        return BookingComHotelProvider(settings)
    return MockHotelProvider()


def get_places_provider(settings: Settings):
    if settings.PLACES_PROVIDER == "google_places" and not settings.DEMO_MODE:
        from app.tools.places.google_places_stub import GooglePlacesProvider
        return GooglePlacesProvider(settings)
    return MockPlacesProvider()


def get_restaurant_provider(settings: Settings):
    return MockRestaurantProvider()


def get_weather_provider(settings: Settings):
    if settings.WEATHER_PROVIDER == "open_meteo" and not settings.DEMO_MODE:
        from app.tools.weather.open_meteo import OpenMeteoWeatherProvider
        return OpenMeteoWeatherProvider()
    return MockWeatherProvider()


def get_currency_provider(settings: Settings):
    if settings.CURRENCY_PROVIDER == "exchange_rate_api" and not settings.DEMO_MODE:
        from app.tools.currency.exchange_rate_api import ExchangeRateApiProvider
        return ExchangeRateApiProvider()
    return MockCurrencyProvider()


def get_maps_provider(settings: Settings):
    return MockMapsProvider()


def get_web_search_provider(settings: Settings):
    if settings.WEB_SEARCH_PROVIDER == "tavily" and not settings.DEMO_MODE:
        from app.tools.web_search.tavily_stub import TavilyWebSearchProvider
        return TavilyWebSearchProvider(settings)
    return MockWebSearchProvider()
