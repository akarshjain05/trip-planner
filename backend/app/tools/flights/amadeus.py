"""Real Amadeus Self-Service flight-search adapter.

Written against Amadeus's documented OAuth2 client-credentials flow and
GET /v2/shopping/flight-offers endpoint. NOT exercised in this session --
this sandbox has no network egress to Amadeus and no credentials were
provided. Wire AMADEUS_API_KEY / AMADEUS_API_SECRET in .env and set
FLIGHTS_PROVIDER=amadeus to use it; test against the Amadeus test
environment before pointing at production.
"""
from __future__ import annotations
import datetime as dt
import httpx
from app.core.config import Settings
from app.schemas.domain import FlightOptionModel
from app.tools.base import ProviderError

_TOKEN_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
_SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"


class AmadeusFlightProvider:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._token: str | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        resp = await client.post(_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": self._settings.AMADEUS_API_KEY,
            "client_secret": self._settings.AMADEUS_API_SECRET,
        })
        if resp.status_code != 200:
            raise ProviderError("amadeus", f"auth failed: {resp.text}", retriable=False)
        return resp.json()["access_token"]

    async def search_flights(
        self, origin: str, destination: str,
        depart_date: dt.date | None = None, return_date: dt.date | None = None,
        adults: int = 1, cabin: str = "economy",
    ) -> list[FlightOptionModel]:
        if not (self._settings.AMADEUS_API_KEY and self._settings.AMADEUS_API_SECRET):
            raise ProviderError("amadeus", "AMADEUS_API_KEY/SECRET not configured", retriable=False)
        async with httpx.AsyncClient(timeout=15) as client:
            token = await self._get_token(client)
            params = {
                "originLocationCode": origin, "destinationLocationCode": destination,
                "departureDate": str(depart_date or dt.date.today() + dt.timedelta(days=30)),
                "adults": adults, "max": 10, "travelClass": cabin.upper(),
            }
            if return_date:
                params["returnDate"] = str(return_date)
            resp = await client.get(_SEARCH_URL, params=params, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code != 200:
                raise ProviderError("amadeus", f"search failed: {resp.text}", retriable=resp.status_code >= 500)
            data = resp.json().get("data", [])

        results = []
        for offer in data:
            itinerary = offer["itineraries"][0]
            segments = itinerary["segments"]
            results.append(FlightOptionModel(
                provider="amadeus", origin=origin, destination=destination,
                depart_at=segments[0]["departure"]["at"], return_at=None,
                airline=segments[0].get("carrierCode"),
                price=float(offer["price"]["total"]), currency=offer["price"]["currency"],
                duration_minutes=None, stops=len(segments) - 1, cabin=cabin,
                baggage=None, is_mock=False,
            ))
        return results
