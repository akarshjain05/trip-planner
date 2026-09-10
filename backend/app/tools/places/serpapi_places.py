from __future__ import annotations
import httpx
from app.core.config import Settings
from app.schemas.domain import PlaceModel
from app.tools.base import ProviderError

class SerpAPIPlacesProvider:
    def __init__(self, settings: Settings):
        self._key = getattr(settings, "SERPAPI_KEY", None)

    async def search_places(self, destination: str, interests: list[str]) -> list[PlaceModel]:
        if not self._key:
            raise ProviderError("serpapi_places", "SERPAPI_KEY not configured", retriable=False)
            
        query = "attractions in " + destination
        if interests:
            query = f"{interests[0]} attractions in {destination}"
            
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_local",
                    "q": query,
                    "api_key": self._key,
                    "num": 10
                }
            )
            
        if resp.status_code != 200:
            raise ProviderError("serpapi_places", f"search failed: {resp.text}", retriable=resp.status_code >= 500)
            
        data = resp.json()
        results = []
        for p in data.get("local_results", []):
            name = p.get("title", "Unknown Place")
            rating = float(p.get("rating", 4.0))
            category = p.get("type", "Attraction")
            
            results.append(PlaceModel(
                name=name,
                category=category,
                rating=rating,
                is_mock=False
            ))
            
        return results
