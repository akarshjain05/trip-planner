from __future__ import annotations
import datetime as dt
import httpx
from app.core.config import Settings
from app.schemas.domain import HotelOptionModel
from app.tools.base import ProviderError

_HOST = "booking-com.p.rapidapi.com"
_LOCATIONS_URL = f"https://{_HOST}/v1/hotels/locations"
_SEARCH_URL = f"https://{_HOST}/v1/hotels/search"


class RapidApiBookingHotelProvider:
    """Hotel provider using the popular Booking.com wrapper on RapidAPI."""
    def __init__(self, settings: Settings):
        self._key = settings.RAPIDAPI_KEY
        if not self._key:
            raise ProviderError("rapidapi_booking", "RAPIDAPI_KEY not configured", retriable=False)

    def _headers(self) -> dict:
        return {
            "x-rapidapi-host": _HOST,
            "x-rapidapi-key": self._key,
        }

    async def _resolve_location(self, client: httpx.AsyncClient, query: str) -> tuple[str, str]:
        resp = await client.get(
            _LOCATIONS_URL,
            params={"name": query, "locale": "en-gb"},
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise ProviderError("rapidapi_booking", f"location search failed: {resp.text}", retriable=resp.status_code >= 500)
        
        data = resp.json()
        if not data:
            raise ProviderError("rapidapi_booking", f"No location found for '{query}'", retriable=False)
            
        # The API returns a list of locations. We pick the first valid city/destination.
        best = data[0]
        dest_id = best.get("dest_id", "")
        dest_type = best.get("dest_type", "city")
        return str(dest_id), str(dest_type)

    async def search_hotels(
        self, destination: str, check_in: dt.date | None = None, check_out: dt.date | None = None,
        adults: int = 1, rooms: int = 1, query: str | None = None,
    ) -> list[HotelOptionModel]:
        if not self._key:
            raise ProviderError("rapidapi_booking", "RAPIDAPI_KEY not configured", retriable=False)

        # Default dates if not provided
        check_in = check_in or dt.date.today() + dt.timedelta(days=30)
        check_out = check_out or check_in + dt.timedelta(days=3)

        async with httpx.AsyncClient(timeout=20) as client:
            dest_id, dest_type = await self._resolve_location(client, destination)

            params = {
                "dest_id": dest_id,
                "dest_type": dest_type,
                "checkin_date": str(check_in),
                "checkout_date": str(check_out),
                "adults_number": str(adults),
                "room_number": str(rooms),
                "order_by": "popularity",
                "filter_by_currency": "USD",
                "locale": "en-gb",
                "units": "metric"
            }

            resp = await client.get(
                _SEARCH_URL,
                params=params,
                headers=self._headers(),
            )
            
            if resp.status_code != 200:
                raise ProviderError("rapidapi_booking", f"hotel search failed: {resp.text}", retriable=resp.status_code >= 500)

            data = resp.json()
            results = data.get("result", [])

        hotels = []
        for h in results[:10]:
            name = h.get("hotel_name", "Unknown Hotel")
            price = h.get("min_total_price")
            if price is None:
                continue

            rating = h.get("review_score", 0.0)
            address = h.get("address", "")
            
            hotels.append(HotelOptionModel(
                provider="rapidapi_booking",
                name=name,
                location=address,
                price_per_night=float(price),
                currency="USD",
                rating=float(rating) if rating else None,
                amenities=[],
                is_mock=False,
            ))

        return hotels
