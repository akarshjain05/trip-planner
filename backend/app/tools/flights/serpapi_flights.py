from __future__ import annotations
import datetime as dt
import httpx
from app.core.config import Settings
from app.schemas.domain import FlightOptionModel
from app.tools.base import ProviderError

class SerpApiFlightProvider:
    """Uses SerpApi Google Flights API to find real flights."""
    def __init__(self, settings: Settings):
        self._key = getattr(settings, "SERPAPI_KEY", None)

    async def search_flights(
        self, origin: str, destination: str,
        depart_date: dt.date | None = None, return_date: dt.date | None = None,
        adults: int = 1, cabin: str = "economy"
    ) -> list[FlightOptionModel]:
        if not self._key:
            raise ProviderError("serpapi_flights", "SERPAPI_KEY not configured", retriable=False)
            
        if not depart_date:
            depart_date = dt.date.today() + dt.timedelta(days=14)
            
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": str(depart_date),
            "currency": "USD",
            "type": 2 if not return_date else 1, # 1=Round trip, 2=One way
            "adults": adults,
            "api_key": self._key
        }
        
        if return_date:
            params["return_date"] = str(return_date)
            
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)
            
        if resp.status_code != 200:
            raise ProviderError("serpapi_flights", f"SerpApi flights failed: {resp.text}", retriable=resp.status_code >= 500)
            
        data = resp.json()
        if "error" in data:
             raise ProviderError("serpapi_flights", f"SerpApi error: {data['error']}", retriable=False)
             
        best_flights = data.get("best_flights", [])
        other_flights = data.get("other_flights", [])
        all_flights = best_flights + other_flights
        
        results = []
        for flight_group in all_flights:
            price = flight_group.get("price", 500.0)
            flights = flight_group.get("flights", [])
            if not flights:
                continue
                
            # Take the first segment
            first_segment = flights[0]
            airline = first_segment.get("airline", "Unknown Airline")
            flight_number = first_segment.get("flight_number", "Unknown")
            
            # Times usually look like "10:30 AM" or similar. Serpapi provides departure_airport.time
            dep_airport = first_segment.get("departure_airport", {})
            arr_airport = first_segment.get("arrival_airport", {})
            dep_time = dep_airport.get("time", "12:00 PM")
            arr_time = arr_airport.get("time", "12:00 PM")
            
            # Combine for UI
            departure_str = f"{str(depart_date)}T{dep_time}" 
            arrival_str = f"{str(depart_date)}T{arr_time}"
            
            results.append(FlightOptionModel(
                provider="serpapi_flights",
                origin=origin,
                destination=destination,
                depart_at=departure_str,
                airline=airline,
                price=float(price),
                currency="USD",
                duration_minutes=int(first_segment.get("duration", 120)),
                stops=len(flights) - 1,
                is_mock=False
            ))
            
        return results[:10]
