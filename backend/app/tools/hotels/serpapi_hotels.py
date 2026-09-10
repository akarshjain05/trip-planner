from __future__ import annotations
import datetime as dt
import httpx
from app.core.config import Settings
from app.schemas.domain import HotelOptionModel
from app.tools.base import ProviderError

class SerpApiHotelProvider:
    """Uses SerpApi Google Hotels API to find real hotels."""
    def __init__(self, settings: Settings):
        self._key = getattr(settings, "SERPAPI_KEY", None)

    async def search_hotels(
        self, destination: str, check_in: dt.date | None, check_out: dt.date | None, adults: int = 2
    ) -> list[HotelOptionModel]:
        if not self._key:
            raise ProviderError("serpapi_hotels", "SERPAPI_KEY not configured", retriable=False)
            
        if not check_in:
            check_in = dt.date.today() + dt.timedelta(days=14)
        if not check_out:
            check_out = check_in + dt.timedelta(days=6)
            
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_hotels",
                    "q": f"Hotels in {destination}",
                    "check_in_date": str(check_in),
                    "check_out_date": str(check_out),
                    "adults": adults,
                    "currency": "USD",
                    "api_key": self._key
                }
            )
            
        if resp.status_code != 200:
            raise ProviderError("serpapi_hotels", f"SerpApi hotels failed: {resp.text}", retriable=resp.status_code >= 500)
            
        data = resp.json()
        if "error" in data:
             raise ProviderError("serpapi_hotels", f"SerpApi error: {data['error']}", retriable=False)
             
        properties = data.get("properties", [])
        
        results = []
        for prop in properties:
            name = prop.get("name", "Unknown Hotel")
            price_data = prop.get("rate_per_night", {})
            price = price_data.get("extracted_lowest", 150.0)
            rating = prop.get("overall_rating", 4.0)
            
            # Google Hotels returns hotel_class as "5-star hotel" string sometimes, or int
            stars = 4
            hc = prop.get("extracted_hotel_class")
            if hc:
                 stars = int(hc)
                 
            results.append(HotelOptionModel(
                provider="serpapi_hotels",
                name=name,
                rating=float(rating) if rating else 4.0,
                stars=stars,
                price_per_night=float(price),
                currency="USD",
                amenities=prop.get("amenities", [])[:5],
                is_mock=False
            ))
            
        return results[:10]
