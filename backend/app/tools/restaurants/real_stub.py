"""Real restaurant-data adapter interface (Google Places 'restaurant' type,
Yelp Fusion, or similar). NOT exercised in this session -- wire it up the
same way as tools/places/google_places_stub.py and set a dedicated
RESTAURANTS_PROVIDER env var if you want it independent of PLACES_PROVIDER."""
from __future__ import annotations
from app.schemas.domain import RestaurantModel
from app.tools.base import ProviderError


class RealRestaurantProvider:
    async def search_restaurants(self, destination: str, cuisine_preferences: list[str]) -> list[RestaurantModel]:
        raise ProviderError("restaurants_real", "Not implemented in this build -- see module docstring.", retriable=False)
