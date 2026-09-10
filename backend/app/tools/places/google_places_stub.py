from __future__ import annotations
import httpx
from app.core.config import Settings
from app.schemas.domain import PlaceModel
from app.tools.base import ProviderError

_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"


class GooglePlacesProvider:
    def __init__(self, settings: Settings):
        self._settings = settings

    async def search_places(self, destination: str, interests: list[str]) -> list[PlaceModel]:
        if not self._settings.GOOGLE_PLACES_API_KEY:
            raise ProviderError("google_places", "GOOGLE_PLACES_API_KEY not configured", retriable=False)
            
        query = f"top {', '.join(interests)} in {destination}" if interests else f"top attractions in {destination}"
        
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                _SEARCH_URL,
                json={"textQuery": query, "maxResultCount": 10},
                headers={
                    "X-Goog-Api-Key": self._settings.GOOGLE_PLACES_API_KEY,
                    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.types",
                    "Content-Type": "application/json"
                }
            )
            
        if resp.status_code != 200:
            raise ProviderError("google_places", f"places search failed: {resp.text}", retriable=resp.status_code >= 500)
            
        data = resp.json()
        results = []
        for p in data.get("places", []):
            name = p.get("displayName", {}).get("text", "Unknown")
            address = p.get("formattedAddress", "")
            rating = p.get("rating", 0.0)
            place_types = p.get("types", [])
            
            results.append(PlaceModel(
                provider="google_places",
                name=name,
                destination=destination,
                categories=place_types[:3] if place_types else ["attraction"],
                rating=rating,
                address=address,
                is_mock=False
            ))
            
        return results
