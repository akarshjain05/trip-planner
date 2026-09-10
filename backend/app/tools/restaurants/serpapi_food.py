from __future__ import annotations
import httpx
from app.core.config import Settings
from app.schemas.domain import RestaurantModel
from app.tools.base import ProviderError

class SerpAPIFoodProvider:
    def __init__(self, settings: Settings):
        self._key = getattr(settings, "SERPAPI_KEY", None)

    async def search_restaurants(self, destination: str, preferences: list[str]) -> list[RestaurantModel]:
        if not self._key:
            raise ProviderError("serpapi_food", "SERPAPI_KEY not configured", retriable=False)
            
        query = "restaurants in " + destination
        if preferences:
            query = f"{preferences[0]} restaurants in {destination}"
            
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_local",
                    "q": query,
                    "api_key": self._key,
                    "num": 5
                }
            )
            
        if resp.status_code != 200:
            raise ProviderError("serpapi_food", f"search failed: {resp.text}", retriable=resp.status_code >= 500)
            
        data = resp.json()
        results = []
        for p in data.get("local_results", []):
            name = p.get("title", "Unknown Restaurant")
            rating = float(p.get("rating", 4.0))
            cuisine = p.get("type", "Local Cuisine")
            
            # Map Google pricing (e.g. "$$") to our pricing ("$$")
            price_str = p.get("price", "$$")
            
            results.append(RestaurantModel(
                name=name,
                cuisine=cuisine,
                price_range=price_str,
                rating=rating,
                is_mock=False
            ))
            
        return results
