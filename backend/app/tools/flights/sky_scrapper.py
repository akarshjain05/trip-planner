"""RapidAPI Sky Scrapper (Skyscanner-style) flight-search adapter.

Uses the free tier of the "Sky Scrapper" API on RapidAPI.  Two calls per
search: one to resolve city/airport names → skyId + entityId, then one
to fetch live flight offers.

Set FLIGHTS_PROVIDER=sky_scrapper and RAPIDAPI_KEY=<your key> in .env.
"""
from __future__ import annotations
import datetime as dt
import httpx
from app.core.config import Settings
from app.schemas.domain import FlightOptionModel
from app.tools.base import ProviderError

_HOST = "sky-scrapper.p.rapidapi.com"
_SEARCH_AIRPORT_URL = f"https://{_HOST}/api/v1/flights/searchAirport"
_SEARCH_FLIGHTS_URL = f"https://{_HOST}/api/v1/flights/searchFlights"


class SkyScrapperFlightProvider:
    def __init__(self, settings: Settings):
        self._key = settings.RAPIDAPI_KEY
        if not self._key:
            raise ProviderError("sky_scrapper", "RAPIDAPI_KEY not configured", retriable=False)

    def _headers(self) -> dict:
        return {
            "x-rapidapi-host": _HOST,
            "x-rapidapi-key": self._key,
        }

    async def _resolve_sky_id(self, client: httpx.AsyncClient, query: str) -> tuple[str, str]:
        """Resolve a city/airport name to (skyId, entityId)."""
        resp = await client.get(
            _SEARCH_AIRPORT_URL,
            params={"query": query, "locale": "en-US"},
            headers=self._headers(),
        )
        if resp.status_code != 200:
            raise ProviderError("sky_scrapper", f"airport search failed: {resp.text}", retriable=resp.status_code >= 500)
        data = resp.json().get("data", [])
        if not data:
            raise ProviderError("sky_scrapper", f"No airport found for '{query}'", retriable=False)
        # Pick the first result (most relevant)
        best = data[0]
        nav = best.get("navigation", {}).get("relevantFlightParams", {})
        sky_id = nav.get("skyId") or best.get("skyId", "")
        entity_id = nav.get("entityId") or best.get("entityId", "")
        return sky_id, entity_id

    async def search_flights(
        self, origin: str, destination: str,
        depart_date: dt.date | None = None, return_date: dt.date | None = None,
        adults: int = 1, cabin: str = "economy",
    ) -> list[FlightOptionModel]:
        if not self._key:
            raise ProviderError("sky_scrapper", "RAPIDAPI_KEY not configured", retriable=False)

        cabin_map = {
            "economy": "economy",
            "premium_economy": "premium_economy",
            "business": "business",
            "first": "first",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            # Step 1: resolve origin and destination to skyId + entityId
            origin_sky, origin_entity = await self._resolve_sky_id(client, origin)
            dest_sky, dest_entity = await self._resolve_sky_id(client, destination)

            # Step 2: search flights
            params = {
                "originSkyId": origin_sky,
                "destinationSkyId": dest_sky,
                "originEntityId": origin_entity,
                "destinationEntityId": dest_entity,
                "date": str(depart_date or (dt.date.today() + dt.timedelta(days=30))),
                "adults": str(adults),
                "cabinClass": cabin_map.get(cabin.lower(), "economy"),
                "currency": "USD",
                "sortBy": "best",
            }
            if return_date:
                params["returnDate"] = str(return_date)

            resp = await client.get(
                _SEARCH_FLIGHTS_URL,
                params=params,
                headers=self._headers(),
            )
            if resp.status_code != 200:
                raise ProviderError("sky_scrapper", f"flight search failed: {resp.text}", retriable=resp.status_code >= 500)

            body = resp.json()
            itineraries = body.get("data", {}).get("itineraries", [])

        results = []
        for itin in itineraries[:10]:  # cap at 10 results
            price_raw = itin.get("price", {}).get("raw")
            if price_raw is None:
                continue

            legs = itin.get("legs", [])
            if not legs:
                continue
            first_leg = legs[0]

            # Extract carrier info
            carriers = first_leg.get("carriers", {}).get("marketing", [])
            airline = carriers[0].get("name", "Unknown") if carriers else "Unknown"

            # Duration
            duration_minutes = first_leg.get("durationInMinutes")

            # Stops
            stop_count = first_leg.get("stopCount", 0)

            # Departure
            depart_at = first_leg.get("departure", "")

            results.append(FlightOptionModel(
                provider="sky_scrapper",
                origin=origin,
                destination=destination,
                depart_at=depart_at,
                return_at=None,
                airline=airline,
                price=float(price_raw),
                currency="USD",
                duration_minutes=duration_minutes,
                stops=stop_count,
                cabin=cabin,
                baggage=None,
                is_mock=False,
            ))

        return results
