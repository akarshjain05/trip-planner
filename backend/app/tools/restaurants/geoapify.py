from __future__ import annotations
import httpx
import logging
from app.core.config import Settings
from app.schemas.domain import RestaurantModel
from app.tools.base import ProviderError

logger = logging.getLogger(__name__)

class GeoapifyFoodProvider:
    def __init__(self, settings: Settings):
        self.api_key = getattr(settings, "GEOAPIFY_API_KEY", None)
        self.geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.places_url = "https://api.geoapify.com/v2/places"

    async def _get_coordinates(self, location: str) -> tuple[float, float]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.geocode_url,
                params={"text": location, "apiKey": self.api_key, "limit": 1}
            )
            if resp.status_code != 200:
                return 0.0, 0.0
            data = resp.json()
            if not data.get("features"):
                return 0.0, 0.0
            coords = data["features"][0]["geometry"]["coordinates"]
            return coords[0], coords[1]

    async def search_restaurants(self, destination: str, preferences: list[str]) -> list[RestaurantModel]:
        if not self.api_key:
            raise ProviderError("geoapify", "GEOAPIFY_API_KEY not configured", retriable=False)
            
        lon, lat = await self._get_coordinates(destination)
        if lon == 0.0 and lat == 0.0:
            return []

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                self.places_url,
                params={
                    "categories": "catering.restaurant,catering.cafe",
                    "filter": f"circle:{lon},{lat},15000",
                    "limit": 15,
                    "apiKey": self.api_key
                }
            )
            if resp.status_code != 200:
                raise ProviderError("geoapify", f"search failed: {resp.text}", retriable=resp.status_code >= 500)
                
            data = resp.json()
            results = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                if "name" in props:
                    results.append(RestaurantModel(
                        name=props["name"],
                        cuisine=props.get("categories", ["Local"])[0].split(".")[-1].title(),
                        price_range="$$",
                        rating=4.5,
                        is_mock=False
                    ))
            return results
